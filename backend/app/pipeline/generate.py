"""4-2단계: 그룹 요약들 → 포트폴리오 소개글 + 발표 자료 (LLM 호출 1회).

diff 원문이 아니라 4-1단계의 요약만 넣어서 입력이 짧다.
"""

from pathlib import Path

from pydantic import BaseModel

from app.config import Settings
from app.models import CollectResult, GroupSummary
from app.pipeline.llm import BaseLLM
from app.pipeline.summarize import SYSTEM_PROMPT
from app.pipeline.text import CommitIndex

_GENERATE_TEMPLATE = (Path(__file__).parent / "prompts" / "generate.md").read_text(encoding="utf-8")


class LLMStatement(BaseModel):
    text: str
    evidence: list[str]  # "C01" 같은 커밋 ID, 또는 "README"


class LLMPortfolio(BaseModel):
    overview: str
    contributions: list[LLMStatement]
    tech_stack: list[str]


class LLMSlide(BaseModel):
    title: str
    bullets: list[LLMStatement]
    notes: str


class LLMOutputs(BaseModel):
    portfolio: LLMPortfolio
    slides: list[LLMSlide]


def generate_outputs(
    collected: CollectResult,
    summaries: list[GroupSummary],
    index: CommitIndex,
    llm: BaseLLM,
    settings: Settings,
) -> LLMOutputs:
    prompt = _GENERATE_TEMPLATE.replace("{{input}}", build_generate_input(collected, summaries, index, settings))
    return llm.parse(system=SYSTEM_PROMPT, prompt=prompt, schema=LLMOutputs)


def build_generate_input(
    collected: CollectResult, summaries: list[GroupSummary], index: CommitIndex, settings: Settings
) -> str:
    repo = collected.repo
    by_sha = {c.sha: c for c in collected.commits}
    lines = [
        f"# 레포: {repo.owner}/{repo.name}",
        f"주소: {repo.url}",
        f"설명: {repo.description or '-'}",
    ]
    if repo.topics:
        lines.append(f"토픽: {', '.join(repo.topics)}")
    lines.append(f"레포 전체 언어: {', '.join(repo.languages) or '-'}")
    lines.append(f"이 개발자가 바꾼 코드의 언어(많은 순): {', '.join(collected.stats.user_languages) or '-'}")

    if repo.readme:
        readme = repo.readme[: settings.max_readme_chars]
        cut = " (앞부분만)" if len(repo.readme) > settings.max_readme_chars else ""
        lines.append(f"\n# README{cut}\n```markdown\n{readme}\n```")

    lines.append(f"\n# 작업 요약 ({len(summaries)}개, 시간순)")
    for s in summaries:
        dates = sorted(by_sha[sha].authored_at.astimezone().date() for sha in s.evidence)
        period = f"{dates[0]:%Y-%m-%d}" + (f" ~ {dates[-1]:%m-%d}" if dates[-1] != dates[0] else "")
        ids = ", ".join(index.id_of(sha) for sha in s.evidence)
        lines.append(f"\n## 작업 {s.group_id}: {s.title} [{s.significance}] ({period}, 커밋: {ids})")
        if s.problem:
            lines.append(f"문제: {s.problem}")
        lines.append(f"해결: {s.solution}")
        lines.append(f"기술: {', '.join(s.technologies) or '-'}")
        for f in s.facts:
            lines.append(f"사실: {f.statement} ({index.id_of(f.evidence)}, 인용: \"{f.quote}\")")
    return "\n".join(lines)
