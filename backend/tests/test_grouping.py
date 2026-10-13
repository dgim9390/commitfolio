from datetime import datetime, timedelta, timezone

from app.models import Commit, FileChange
from app.pipeline.grouping.base import UnionFind
from app.pipeline.grouping.heuristic import HeuristicConfig, HeuristicGrouper, message_tokens
from app.pipeline.grouping.rules import exclusion_reason, message_label

T0 = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


def make(i: int, minutes: int, paths: list[str], msg: str = "", pr: int | None = None, lines: int = 10) -> Commit:
    return Commit(
        sha=f"{i:040d}",
        url="",
        message=msg or f"작업{i}",
        authored_at=T0 + timedelta(minutes=minutes),
        author_login="u",
        files=[FileChange(path=p, additions=lines) for p in paths],
        pr_number=pr,
    )


def shas(groups) -> list[set[int]]:
    return sorted(({int(s) for s in g.commit_shas} for g in groups), key=min)


# ---------------------------------------------------------------- 규칙


def test_union_find():
    uf = UnionFind(5)
    assert uf.union(0, 1) and uf.union(3, 4)
    assert not uf.union(1, 0)
    assert sorted(map(sorted, uf.components())) == [[0, 1], [2], [3, 4]]


def test_message_label():
    assert message_label("3D: 키보드 수정") == "3d"
    assert message_label("[Auth] 토큰 갱신") == "auth"
    assert message_label("feat(api): add endpoint") == "api"
    assert message_label("feat: add endpoint") is None  # 'feat'만으로는 같은 작업이라 볼 수 없음
    assert message_label("맥 앱 1.1.0: 업데이트") == message_label("맥 앱 1.2.0: 서명") == "맥 앱"
    assert message_label("fix: typo") is None
    assert message_label("버그 수정: 로그인") is None  # 너무 일반적인 이름표
    assert message_label("https://example.com 링크 반영") is None
    assert message_label("이름표 없는 커밋") is None


def test_exclusion_reason():
    assert exclusion_reason(make(0, 0, ["README.md"])) == "docs_only"
    assert exclusion_reason(make(0, 0, ["docs/guide.png", "docs/setup.md"])) == "docs_only"
    assert exclusion_reason(make(0, 0, ["desktop/package.json"], lines=1)) == "version_bump"
    assert exclusion_reason(make(0, 0, ["package.json"], lines=30)) is None  # 의존성 대량 변경은 작업
    assert exclusion_reason(make(0, 0, ["README.md", "src/app.ts"])) is None
    no_code = make(0, 0, ["yarn.lock"])
    no_code.files[0].excluded_reason = "lock"
    assert exclusion_reason(no_code) == "no_code"


def test_message_tokens():
    tokens = message_tokens("3D 꺼진 화면을 자연스럽게\n\nCo-Authored-By: Claude <x@y.z>")
    assert {"3d", "화면", "꺼진"} <= tokens
    assert "claude" not in tokens and "authored" not in tokens  # 서명 줄 제거
    assert "fix" not in message_tokens("fix typo")  # 불용어


# ---------------------------------------------------------------- 그룹화


def test_groups_by_shared_area_and_excludes_docs():
    commits = [
        make(0, 0, ["lib/desk3d/scene.ts"], "3D 조명"),
        make(1, 10, ["README.md"], "README 정리"),
        make(2, 20, ["lib/desk3d/scene.ts", "lib/desk3d/models.ts"], "3D 모델"),
        make(3, 30, ["api/auth.py"], "로그인 API"),
        make(4, 40, ["lib/desk3d/models.ts"], "3D 키보드"),
        make(5, 50, ["api/auth.py", "api/session.py"], "로그인 세션"),
    ]
    result = HeuristicGrouper().group(commits)
    assert shas(result.groups) == [{0, 2, 4}, {3, 5}]
    assert [(int(e.sha), e.reason) for e in result.excluded] == [(1, "docs_only")]


def test_no_time_limit():
    # 열흘 떨어져 있어도 같은 영역의 작업이면 한 그룹
    commits = [make(0, 0, ["lib/a.ts"], "3D 조명"), make(1, 60 * 24 * 10, ["lib/a.ts"], "3D 조명 보정")]
    assert shas(HeuristicGrouper().group(commits).groups) == [{0, 1}]


def test_label_and_pr_force_grouping():
    commits = [
        make(0, 0, ["api/a.py"], "결제: 서버", pr=None),
        make(1, 60, ["web/b.tsx"], "결제: 화면"),  # 경로가 전혀 달라도 이름표가 같음
        make(2, 120, ["x/c.py"], "백엔드", pr=7),
        make(3, 180, ["y/d.go"], "프론트", pr=7),
    ]
    result = HeuristicGrouper().group(commits)
    assert shas(result.groups) == [{0, 1}, {2, 3}]
    reasons = {link.reason for g in result.groups for link in g.links}
    assert {"같은 이름표 '결제'", "같은 PR #7"} <= reasons


def test_average_linkage_avoids_chaining():
    # A–B, B–C, C–D만 이웃끼리 겹친다. 단일 연결이면 A~D가 전부 한 그룹이 된다.
    commits = [
        make(0, 0, ["a/x.ts", "a/y.ts"], "로그인"),
        make(1, 5, ["a/y.ts", "b/z.ts"], "결제"),
        make(2, 10, ["b/z.ts", "c/w.ts"], "알림"),
        make(3, 15, ["c/w.ts", "d/v.ts"], "검색"),
    ]
    groups = HeuristicGrouper().group(commits).groups
    assert len(groups) > 1
    assert not any({0, 3} <= g for g in shas(groups))


def test_max_group_size_splits_at_largest_gap():
    commits = [make(i, i * 5 + (600 if i >= 3 else 0), ["same/file.ts"], "같은 작업") for i in range(6)]
    groups = HeuristicGrouper(HeuristicConfig(max_group_size=4)).group(commits).groups
    assert shas(groups) == [{0, 1, 2}, {3, 4, 5}]


def test_every_commit_once():
    commits = [make(i, i * 7, [f"d{i % 3}/f.ts"] if i % 4 else ["README.md"]) for i in range(12)]
    commits[5].is_merge = True
    result = HeuristicGrouper().group(commits)
    seen = [s for g in result.groups for s in g.commit_shas] + [e.sha for e in result.excluded]
    assert len(seen) == len(set(seen)) == 11
    assert commits[5].sha not in seen
