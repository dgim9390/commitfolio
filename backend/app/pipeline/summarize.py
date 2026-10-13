"""4-1단계: 작업 그룹마다 '무슨 문제를 어떻게 해결했는지' 요약.

무료 등급은 하루 호출 수가 적어서, 그룹 하나씩이 아니라 입력 상한(max_chars_per_summary_call)을
채울 때까지 여러 그룹을 묶어 한 번에 요청한다. 묶는 방법은 순서를 유지한 채 앞에서부터
채우는 단순한 greedy 방식이다 (그룹 순서가 시간순이라 비슷한 시기의 작업이 같이 들어간다).
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.config import Settings
from app.models import Commit, CollectResult, Fact, GroupingResult, GroupSummary, WorkGroup
from app.pipeline.filters import MIN_USEFUL_PATCH_CHARS, REASON_LABELS, allocate_budget, truncate_patch
from app.pipeline.llm import BaseLLM
from app.pipeline.text import CommitIndex, strip_trailers

PROMPTS = Path(__file__).parent / "prompts"
SYSTEM_PROMPT = (PROMPTS / "system.md").read_text(encoding="utf-8")
_SUMMARIZE_TEMPLATE = (PROMPTS / "summarize.md").read_text(encoding="utf-8")

_STATUS = {"added": "추가", "modified": "수정", "deleted": "삭제", "renamed": "이름변경"}


# LLM이 채우는 형식 (커밋은 짧은 ID로). 검증 후 GroupSummary(SHA)로 바꾼다.
class LLMFact(BaseModel):
    statement: str
    commit_id: str
    quote: str


class LLMGroupSummary(BaseModel):
    group_id: int
    title: str
    problem: str
    solution: str
    technologies: list[str]
    significance: Literal["major", "minor"]
    evidence: list[str]
    facts: list[LLMFact]


class LLMSummaryBatch(BaseModel):
    summaries: list[LLMGroupSummary]


def summarize_groups(
    collected: CollectResult,
    grouping: GroupingResult,
    index: CommitIndex,
    llm: BaseLLM,
    settings: Settings,
    notes: list[str],
    progress=lambda stage, msg: None,
) -> list[GroupSummary]:
    by_sha = {c.sha: c for c in collected.commits}
    prs = {pr.number: pr for pr in collected.pull_requests}
    groups = grouping.groups
    blocks = [
        build_group_block(g, [by_sha[s] for s in g.commit_shas], prs, index, settings) for g in groups
    ]
    batches = pack_batches([len(b) for b in blocks], settings.max_chars_per_summary_call)

    summaries: dict[int, GroupSummary] = {}
    for n, batch in enumerate(batches, 1):
        progress("summarize", f"작업 요약 중 ({n}/{len(batches)}번째 요청, 그룹 {len(batch)}개)")
        prompt = _SUMMARIZE_TEMPLATE.replace(
            "{{input}}", repo_header(collected) + "\n\n" + "\n\n".join(blocks[i] for i in batch)
        )
        result = llm.parse(system=SYSTEM_PROMPT, prompt=prompt, schema=LLMSummaryBatch)
        wanted = {groups[i].id: groups[i] for i in batch}
        for raw in result.summaries:
            group = wanted.get(raw.group_id)
            if group is None or group.id in summaries:
                notes.append(f"요약: 요청하지 않았거나 중복된 그룹 번호 {raw.group_id}를 무시했습니다.")
                continue
            summaries[group.id] = _to_summary(raw, group, [by_sha[s] for s in group.commit_shas], index, notes)

    # 응답에서 빠진 그룹은 커밋 제목으로 최소한의 요약을 만든다 (호출을 더 쓰지 않기 위해)
    for g in groups:
        if g.id not in summaries:
            notes.append(f"요약: 그룹 {g.id}의 요약이 응답에 없어 커밋 제목으로 대신했습니다.")
            titles = [by_sha[s].title for s in g.commit_shas]
            summaries[g.id] = GroupSummary(
                group_id=g.id, title=titles[0][:30], problem="", solution=" / ".join(titles),
                technologies=[], significance="minor", evidence=list(g.commit_shas),
            )
    return [summaries[g.id] for g in groups]


def pack_batches(sizes: list[int], limit: int) -> list[list[int]]:
    """크기 목록을 순서대로 앞에서부터 limit까지 채워 묶는다. limit보다 큰 항목은 혼자 한 묶음."""
    batches: list[list[int]] = []
    current: list[int] = []
    total = 0
    for i, size in enumerate(sizes):
        if current and total + size > limit:
            batches.append(current)
            current, total = [], 0
        current.append(i)
        total += size
    if current:
        batches.append(current)
    return batches


def repo_header(collected: CollectResult) -> str:
    repo = collected.repo
    return f"# 레포: {repo.owner}/{repo.name}\n설명: {repo.description or '-'}"


def build_group_block(
    group: WorkGroup, commits: list[Commit], prs: dict, index: CommitIndex, settings: Settings
) -> str:
    patches = _fit_patches(commits, settings.max_patch_chars_per_group)
    lines = [f"# 작업 그룹 {group.id} (커밋 {len(commits)}개)"]
    for c in commits:
        lines.append(f"\n## {index.id_of(c.sha)} · {c.authored_at.astimezone():%Y-%m-%d %H:%M}")
        if c.pr_number and c.pr_number in prs:
            pr = prs[c.pr_number]
            lines.append(f"PR #{pr.number}: {pr.title}")
            if pr.body.strip():
                lines.append(f"PR 설명:\n{pr.body.strip()[:2000]}")
        lines.append(f"메시지:\n{strip_trailers(c.message)}")
        if not c.diff_available:
            lines.append("(diff를 읽을 수 없는 커밋)")
            continue
        lines.append("변경 파일:")
        for f in c.files:
            path = f"{f.old_path} → {f.path}" if f.old_path else f.path
            excluded = f" [분석 제외: {REASON_LABELS.get(f.excluded_reason, f.excluded_reason)}]" if f.excluded_reason else ""
            lines.append(f"- {_STATUS[f.status]} {path} (+{f.additions}/-{f.deletions}){excluded}")
        diff_parts = [
            f"--- {f.path}\n{patches[(c.sha, f.path)]}" for f in c.included_files if patches.get((c.sha, f.path))
        ]
        if diff_parts:
            lines.append("diff:\n```diff\n" + "\n".join(diff_parts) + "\n```")
    return "\n".join(lines)


def _fit_patches(commits: list[Commit], budget: int) -> dict[tuple[str, str], str]:
    """그룹 전체 diff를 budget 안에 맞춘다.

    수집 단계의 '커밋 안 파일끼리 공평하게 나누기'(allocate_budget)를 한 단계 위에서 다시 쓴다:
    먼저 커밋끼리 예산을 나누고, 몫이 모자란 커밋은 그 몫을 다시 파일끼리 나눈다.
    """
    per_commit = [[f for f in c.included_files if f.patch] for c in commits]
    totals = [sum(len(f.patch) for f in files) for files in per_commit]
    result: dict[tuple[str, str], str] = {}
    for c, files, total, share in zip(commits, per_commit, totals, allocate_budget(totals, budget)):
        limits = [len(f.patch) for f in files] if share >= total else allocate_budget([len(f.patch) for f in files], share)
        for f, limit in zip(files, limits):
            if limit >= len(f.patch):
                result[(c.sha, f.path)] = f.patch
            elif limit >= MIN_USEFUL_PATCH_CHARS:
                result[(c.sha, f.path)] = truncate_patch(f.patch, limit)[0]
    return result


def commit_source_text(c: Commit) -> str:
    """검증용: 이 커밋에서 '근거'로 인정할 수 있는 원문 (메시지 + 파일 경로 + diff)."""
    parts = [c.message] + [f.path for f in c.files] + [f.patch or "" for f in c.files]
    return "\n".join(parts)


def _normalize(text: str) -> str:
    return " ".join(text.split())


def _to_summary(raw: LLMGroupSummary, group: WorkGroup, commits: list[Commit], index: CommitIndex, notes: list[str]) -> GroupSummary:
    in_group = set(group.commit_shas)
    evidence = []
    for cid in raw.evidence:
        sha = index.sha_of(cid)
        if sha in in_group and sha not in evidence:
            evidence.append(sha)
        elif sha not in in_group:
            notes.append(f"그룹 {group.id} 요약: 그룹에 없는 커밋 ID {cid!r}를 근거에서 뺐습니다.")
    if not evidence:
        evidence = list(group.commit_shas)  # 요약 자체는 그룹 전체가 근거

    sources = {c.sha: _normalize(commit_source_text(c)) for c in commits}
    facts = []
    for fact in raw.facts:
        sha = index.sha_of(fact.commit_id)
        if sha not in in_group:
            notes.append(f"그룹 {group.id}: 근거 커밋이 없는 사실을 뺐습니다: {fact.statement}")
        elif _normalize(fact.quote) not in sources[sha]:
            # 인용문이 실제 커밋에 없으면 LLM이 지어낸 것일 수 있으므로 버린다
            notes.append(f"그룹 {group.id}: 인용이 커밋 {sha[:7]}에서 확인되지 않아 뺐습니다: {fact.statement}")
        else:
            facts.append(Fact(statement=fact.statement, evidence=sha, quote=fact.quote))

    return GroupSummary(
        group_id=group.id,
        title=raw.title,
        problem=raw.problem,
        solution=raw.solution,
        technologies=raw.technologies,
        significance=raw.significance,
        evidence=evidence,
        facts=facts,
    )
