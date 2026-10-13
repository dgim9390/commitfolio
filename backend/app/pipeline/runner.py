"""전체 파이프라인: 수집 → 그룹화 → 요약 → 생성 → 검증.

CLI와 FastAPI(5단계)가 모두 이 함수 하나만 호출한다.
"""

from datetime import date

from app.config import Settings, get_settings
from app.github.collector import ProgressFn, collect
from app.models import AnalysisResult, CommitRef, Outputs, Portfolio
from app.pipeline.generate import generate_outputs
from app.pipeline.grouping.base import Grouper
from app.pipeline.grouping.heuristic import HeuristicGrouper
from app.pipeline.llm import LLMCache, make_llm
from app.pipeline.summarize import summarize_groups
from app.pipeline.text import CommitIndex
from app.pipeline.validate import validate_outputs


def analyze(
    repo_url: str,
    username: str,
    since: date | None = None,
    until: date | None = None,
    settings: Settings | None = None,
    progress: ProgressFn | None = None,
    grouper: Grouper | None = None,
) -> AnalysisResult:
    settings = settings or get_settings()
    report = progress or (lambda stage, msg: None)

    collected = collect(repo_url, username, since, until, settings, report)

    report("group", "커밋을 작업 단위로 묶는 중")
    grouping = (grouper or HeuristicGrouper()).group(collected.commits)

    by_sha = {c.sha: c for c in collected.commits}
    analyzed = [by_sha[sha] for g in grouping.groups for sha in g.commit_shas]
    index = CommitIndex(analyzed)
    notes: list[str] = []

    cache = LLMCache(settings.cache_dir / "llm.sqlite3")
    try:
        llm = make_llm(settings, cache)
        summaries = summarize_groups(collected, grouping, index, llm, settings, notes, report) if analyzed else []

        report("generate", "포트폴리오 소개글·발표 자료 생성 중")
        raw = generate_outputs(collected, summaries, index, llm, settings) if summaries else None
    finally:
        cache.close()

    report("validate", "근거 검증 중")
    if raw is None:
        outputs = Outputs(portfolio=Portfolio(tagline="", overview="", contributions=[], tech_stack=[]), slides=[])
        notes.append("분석할 커밋이 없어 결과를 만들지 않았습니다.")
    else:
        groups = [g.commit_shas for g in grouping.groups]
        outputs = validate_outputs(raw, analyzed, index, collected.repo, notes, groups)

    return AnalysisResult(
        repo=collected.repo,
        username=username,
        since=since,
        until=until,
        commits=[CommitRef(sha=c.sha, url=c.url, title=c.title, authored_at=c.authored_at) for c in collected.commits],
        grouping=grouping,
        summaries=summaries,
        outputs=outputs,
        validation_notes=notes,
        usage=llm.usage,
    )
