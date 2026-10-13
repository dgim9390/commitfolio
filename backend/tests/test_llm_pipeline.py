"""LLM 단계 테스트. 실제 API 대신 정해진 답을 돌려주는 FakeLLM을 쓴다 (비용 0, 결과 고정)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.config import Settings
from app.errors import LLMError
from app.models import (
    ApiStats,
    CollectResult,
    CollectStats,
    Commit,
    FileChange,
    GroupingResult,
    GroupSummary,
    RepoInfo,
    WorkGroup,
)
from app.pipeline.generate import (
    LLMContribution,
    LLMHighlight,
    LLMOutputs,
    LLMPortfolio,
    LLMSlide,
    LLMSlidePoint,
    LLMStatement,
    LLMTechGroup,
    build_generate_input,
)
from app.pipeline.llm import BaseLLM, LLMCache, make_llm
from app.pipeline.summarize import LLMFact, LLMGroupSummary, LLMSummaryBatch, _fit_patches, pack_batches, summarize_groups
from app.pipeline.text import CommitIndex, strip_trailers
from app.pipeline.validate import unverified_numbers, validate_outputs

T0 = datetime(2026, 9, 29, 3, 0, tzinfo=timezone.utc)


def commit(i: int, days: int, msg: str, patch: str) -> Commit:
    return Commit(
        sha=f"{i:040x}",
        url=f"https://github.com/o/r/commit/{i:040x}",
        message=msg,
        authored_at=T0 + timedelta(days=days),
        author_login="u",
        files=[FileChange(path=f"src/f{i}.ts", additions=patch.count("\n+"), patch=patch)],
    )


COMMITS = [
    commit(1, 0, "제품 19종 추가", "@@ -0,0 +1 @@\n+const catalog = [/* 19 items */];"),
    commit(2, 1, "fix\n\nCo-Authored-By: Bot <b@x>", "@@ -1 +1 @@\n-retry(3)\n+retry(5)"),
    commit(3, 8, "3D 보기", "@@ -0,0 +1 @@\n+new THREE.Scene()"),
]
GROUPS = [
    WorkGroup(id=1, commit_shas=[COMMITS[0].sha, COMMITS[1].sha], started_at=COMMITS[0].authored_at, ended_at=COMMITS[1].authored_at),
    WorkGroup(id=2, commit_shas=[COMMITS[2].sha], started_at=COMMITS[2].authored_at, ended_at=COMMITS[2].authored_at),
]
REPO = RepoInfo(
    owner="o", name="r", url="https://github.com/o/r", description="책상 꾸미기 앱", default_branch="main",
    readme="# 데스크보드\n제품 사진으로 책상을 꾸미는 앱",
)
COLLECTED = CollectResult(
    repo=REPO, username="u", since=None, until=None, commits=COMMITS, pull_requests=[],
    stats=CollectStats(
        repo_commits_in_range=3, user_commits=3, merge_commits=0, files_total=3, files_excluded=0,
        excluded_by_reason={}, files_truncated=0, user_languages={"TypeScript": 3}, api=ApiStats(),
    ),
    collected_at=T0,
)
INDEX = CommitIndex(COMMITS)


class FakeLLM:
    def __init__(self, answer):
        self.answer = answer
        self.prompts: list[str] = []

    def parse(self, *, system, prompt, schema):
        self.prompts.append(prompt)
        return self.answer(prompt)


def summary(group_id: int, **kw) -> LLMGroupSummary:
    base = dict(group_id=group_id, title="t", problem="p", solution="s", technologies=[], significance="major",
                evidence=[], key_points=[], decisions=[], facts=[])
    return LLMGroupSummary(**{**base, **kw})


def test_commit_index_and_trailers():
    assert INDEX.id_of(COMMITS[0].sha) == "C01"
    assert INDEX.sha_of(" c03 ") == COMMITS[2].sha
    assert INDEX.sha_of("C99") is None
    assert strip_trailers(COMMITS[1].message) == "fix"


def test_pack_batches():
    assert pack_batches([40, 40, 40, 10], limit=100) == [[0, 1], [2, 3]]
    assert pack_batches([150, 10], limit=100) == [[0], [1]]  # 혼자 큰 그룹은 단독 요청
    assert pack_batches([], limit=100) == []


def test_summarize_batches_validates_evidence_and_quotes():
    answer = LLMSummaryBatch(summaries=[
        summary(
            1, title="카탈로그",
            evidence=["C01", "C03", "C77"],  # C03은 다른 그룹, C77은 없는 ID
            facts=[
                LLMFact(statement="제품 19종", commit_id="C01", quote="제품 19종 추가"),  # 진짜 인용
                LLMFact(statement="재시도 5회", commit_id="C02", quote="+retry(5)"),  # diff 인용
                LLMFact(statement="로딩 50% 단축", commit_id="C01", quote="로딩 50% 단축"),  # 지어낸 인용
            ],
        ),
        summary(9),  # 요청하지 않은 그룹 번호
        # 그룹 2는 응답에서 빠짐
    ])
    llm = FakeLLM(lambda prompt: answer)
    notes: list[str] = []
    summaries = summarize_groups(COLLECTED, GroupingResult(groups=GROUPS), INDEX, llm, Settings(), notes)

    assert len(llm.prompts) == 1  # 두 그룹이 한 번의 요청으로
    assert [s.group_id for s in summaries] == [1, 2]
    s1, s2 = summaries
    assert s1.evidence == [COMMITS[0].sha]
    assert [f.statement for f in s1.facts] == ["제품 19종", "재시도 5회"]
    assert s2.solution == "3D 보기" and s2.significance == "minor"  # 빠진 그룹은 커밋 제목으로 대체
    assert any("로딩" in n for n in notes)
    assert any("그룹 번호 9" in n for n in notes)
    assert any("그룹 2의 요약이 응답에 없어" in n for n in notes)
    assert "Co-Authored-By" not in llm.prompts[0] and "+retry(5)" in llm.prompts[0]


def test_fit_patches_shares_group_budget():
    big = commit(9, 0, "big", "@@\n" + "\n".join(f"+line {i}" for i in range(3000)))
    small = commit(8, 0, "small", "@@\n+tiny")
    fitted = _fit_patches([big, small], budget=2000)
    assert fitted[(small.sha, "src/f8.ts")] == small.files[0].patch  # 작은 커밋은 온전히
    assert len(fitted[(big.sha, "src/f9.ts")]) < 2100


def test_unverified_numbers():
    assert unverified_numbers("제품 19종을 추가하고 재시도를 5회로", ["제품 19종 추가", "retry(5)"]) == []
    assert unverified_numbers("로딩 시간 50% 단축", ["로딩 개선"]) == ["50"]
    assert unverified_numbers("사용자 1,000명", ["users = 1000"]) == []
    # "3D"의 3은 이름의 일부: 텍스트 쪽에서도, 근거 쪽에서도 수치로 치지 않는다
    assert unverified_numbers("3D 보기 구현", []) == []
    assert unverified_numbers("3차원 좌표로 이동", []) == []
    assert unverified_numbers("사설 IP(192.168.x) 차단", [r"/^192\.168\./.test(ip)"]) == []
    assert unverified_numbers("사설 IP(192.168.x) 차단", ["a === 192 && b === 168"]) == []  # 조각으로 나뉜 경우
    assert unverified_numbers("2.5배 빨라짐", ["x = 2; y = 5"]) == ["2.5"]  # 한 자리 조각은 인정 안 함
    assert unverified_numbers("SHA-256 해시로 16자리 지문", ["createHash('sha256') ... slice(0, 16)"]) == []
    assert unverified_numbers("3명이 사용", ["3D 보기", "v1.3"]) == ["3"]


def test_generate_input_contains_readme_and_ids():
    s = GroupSummary(group_id=1, title="카탈로그", problem="p", solution="s", technologies=["React"],
                     significance="major", evidence=[COMMITS[0].sha])
    text = build_generate_input(COLLECTED, [s], INDEX, Settings())
    assert "데스크보드" in text and "커밋: C01" in text


def st(text: str, *refs: str) -> LLMStatement:
    return LLMStatement(text=text, evidence=list(refs))


def slide(layout, title, points=(), highlights=(), notes="", headline="h") -> LLMSlide:
    return LLMSlide(layout=layout, title=title, headline=headline, points=list(points), highlights=list(highlights),
                    flow=[], notes=notes)


def test_validate_outputs():
    raw = LLMOutputs(
        portfolio=LLMPortfolio(
            tagline="데스크 시뮬레이터",
            overview="100명이 쓰는 앱",  # README·커밋에 없는 숫자
            contributions=[
                LLMContribution(title="카탈로그", summary=st("제품 19종 카탈로그 구현", "C01"),
                                points=[st("재시도 5회로 변경", "C02"), st("성능 40% 개선", "C02"), st("근거 없는 문장", "C42")],
                                technologies=["TS"]),
                # 요약 문장 근거가 없으면 첫 포인트가 요약으로 올라간다
                LLMContribution(title="3D", summary=st("요약", "C99"), points=[st("three.js 장면", "C03")], technologies=[]),
                LLMContribution(title="가짜", summary=st("없음", "C55"), points=[], technologies=[]),
            ],
            tech_stack=[LLMTechGroup(category="Frontend", items=["TypeScript"]), LLMTechGroup(category="빈 분야", items=[])],
        ),
        slides=[
            slide("cover", "데스크보드"),
            slide("feature", "3D", points=[LLMSlidePoint(heading="장면", text="three.js 장면", evidence=["C03", "C01"])],
                  highlights=[LLMHighlight(value="19종", label="제품", evidence=["C01"]),
                              LLMHighlight(value="3배", label="속도", evidence=["C03"])],  # 근거 없는 수치 카드
                  notes="2주 걸렸다"),
            slide("feature", "가짜", points=[LLMSlidePoint(heading="x", text="없음", evidence=["C55"])]),
            slide("agenda", "목차", points=[LLMSlidePoint(heading="소개", text="프로젝트 소개", evidence=["README"])]),
        ],
    )
    notes: list[str] = []
    out = validate_outputs(raw, COMMITS, INDEX, REPO, notes)
    p = out.portfolio

    assert [c.title for c in p.contributions] == ["카탈로그", "3D"]
    catalog, three = p.contributions
    # 근거에 없는 숫자(40%)가 든 문장과 근거 커밋이 없는 문장은 빠진다
    assert [pt.text for pt in catalog.points] == ["재시도 5회로 변경"]
    assert any("40" in n and "문장을 뺐습니다" in n for n in notes)
    assert three.summary.text == "three.js 장면" and three.points == []
    assert [g.category for g in p.tech_stack] == ["Frontend"]
    assert any("포트폴리오 개요" in n for n in notes)

    assert [s.title for s in out.slides] == ["데스크보드", "3D", "목차"]  # 근거가 다 빠진 장은 삭제, 표지는 유지
    feature = out.slides[1]
    assert feature.points[0].heading == "장면" and feature.points[0].text == "three.js 장면"
    # 'three.js 장면'과 상관없는 카탈로그 커밋(C01)은 근거 일치도 검사에서 빠진다
    assert feature.points[0].evidence == [COMMITS[2].sha]
    assert [h.value for h in feature.highlights] == ["19종"]
    assert any("3배" in n for n in notes)
    assert any("발표자 메모" in n for n in notes)  # "2주" 근거 없음
    assert out.slides[2].points[0].from_readme


def test_llm_cache_and_provider_selection(tmp_path):
    calls = []

    class CountingLLM(BaseLLM):
        provider = "gemini"

        def _call(self, system, prompt, schema):
            calls.append(prompt)
            return schema(portfolio=LLMPortfolio(tagline="t", overview="o", contributions=[], tech_stack=[]), slides=[]), 10, 5

    llm = CountingLLM(Settings(), LLMCache(tmp_path / "llm.sqlite3"))
    first = llm.parse(system="s", prompt="p", schema=LLMOutputs)
    second = llm.parse(system="s", prompt="p", schema=LLMOutputs)
    assert first == second and len(calls) == 1  # 두 번째는 캐시
    assert (llm.usage.calls, llm.usage.cached_calls, llm.usage.input_tokens) == (1, 1, 10)

    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        make_llm(Settings(llm_provider="gemini", gemini_api_key=""))
    with pytest.raises(LLMError, match="LLM_PROVIDER"):
        make_llm(Settings(llm_provider="openai"))
