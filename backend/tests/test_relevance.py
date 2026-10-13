from datetime import datetime, timezone

from app.models import Commit, FileChange
from app.pipeline.relevance import RelevanceIndex, tokens

T = datetime(2026, 10, 1, tzinfo=timezone.utc)


def commit(i: int, msg: str, path: str, patch: str) -> Commit:
    return Commit(sha=f"{i:040d}", url="", message=msg, authored_at=T, author_login="u",
                  files=[FileChange(path=path, additions=1, patch=patch)])


DRAG = commit(1, "3D에서 제품을 끌어서 옮기기", "lib/desk3d/scene.ts", "+const raycaster = new Raycaster()\n+onPointerDrag(item)")
GLASS = commit(2, "꺼진 화면에 반사광", "lib/desk3d/textures.ts", "+const screenGlass = reflectionGradient()")
RELIEF = commit(3, "사진 제품을 입체 곡면으로", "lib/desk3d/models.ts", "+function reliefMesh(alpha) { distanceTransform(alpha) }")
CATALOG = commit(4, "제품 19종 추가", "data/catalog.ts", "+export const catalog = [speakerStand, shelf]")
README = commit(5, "README 정리", "README.md", "+3D 드래그 raycaster reliefMesh 반사광 카탈로그 전부 설명")
COMMITS = [DRAG, GLASS, RELIEF, CATALOG, README]
GROUPS = [[DRAG.sha, GLASS.sha, RELIEF.sha], [CATALOG.sha], [README.sha]]
INDEX = RelevanceIndex(COMMITS, GROUPS)


def test_tokens_split_identifiers_and_korean():
    ts = tokens("useDeskStore로 화면을 그렸다")
    assert {"usedeskstore", "use", "desk", "store", "화면"} <= ts


def test_related_commit_scores_higher():
    text = "레이캐스터로 3D 화면에서 제품을 드래그해 옮기기 (Raycaster, onPointerDrag)"
    assert INDEX.score(text, DRAG.sha) > INDEX.score(text, GLASS.sha)


def test_drop_unrelated_evidence():
    res = INDEX.check_evidence("Raycaster로 onPointerDrag 끌어서 옮기기", [DRAG.sha, GLASS.sha])
    assert res.evidence == [DRAG.sha]
    assert res.notes and "뺐습니다" in res.notes[0]


def test_switch_to_better_commit_in_same_group():
    res = INDEX.check_evidence("distanceTransform으로 사진을 reliefMesh 입체 곡면으로", [GLASS.sha])
    assert res.evidence == [RELIEF.sha]
    assert "바꿨습니다" in res.notes[0]


def test_never_switch_to_other_group_or_docs():
    # 카탈로그는 다른 작업 그룹, README 같은 문서 파일은 비교에서 뺀다 → 바꿀 후보가 없어 경고만
    res = INDEX.check_evidence("speakerStand shelf catalog 제품 목록", [GLASS.sha])
    assert res.evidence == [GLASS.sha]
    assert res.warning


def test_keep_good_evidence_untouched():
    res = INDEX.check_evidence("reliefMesh distanceTransform 입체 곡면", [RELIEF.sha])
    assert res.evidence == [RELIEF.sha] and not res.notes and res.warning is None


def test_multi_evidence_gets_better_commit_prepended():
    res = INDEX.check_evidence("reliefMesh distanceTransform 사진 입체 곡면", [DRAG.sha, GLASS.sha])
    assert res.evidence[0] == RELIEF.sha and DRAG.sha in res.evidence
