"""4-3단계: LLM 출력 검증.

프롬프트로 "지어내지 마라"고 해도 100% 지켜지지는 않는다. 그래서 코드로 한 번 더 거른다.
- 근거 커밋 ID가 실제로 있는지 (없는 ID는 빼고, 근거가 하나도 안 남은 문장은 버린다)
- "README" 근거는 README나 레포 설명이 실제로 있을 때만 인정
- 문장 속 숫자가 근거(커밋 메시지·diff, README)에 실제로 나오는지 (안 나오면 그 문장을 뺀다)
- 근거 커밋이 문장 내용과 맞는지 (relevance.py: 안 맞는 근거는 빼거나 더 맞는 커밋으로 고친다)
"""

import re

from app.models import (
    Commit,
    Contribution,
    Highlight,
    Outputs,
    Portfolio,
    RepoInfo,
    Slide,
    SlidePoint,
    Statement,
    TechGroup,
)
from app.pipeline.generate import LLMOutputs
from app.pipeline.relevance import RelevanceIndex
from app.pipeline.summarize import commit_source_text
from app.pipeline.text import CommitIndex

# 홀로 선 숫자만 본다: "19종", "30%", "retry(5)"의 숫자는 잡고, "3D", "v1.3", "i18n", "SHA-256"처럼
# 영문·숫자와 붙어 이름의 일부인 숫자는 수치가 아니므로 무시한다.
_EDGE_BEFORE = r"(?<![0-9A-Za-z.,])(?<![A-Za-z]-)"
_EDGE_AFTER = r"(?![0-9A-Za-z]|[.,]\d|차원)"  # "3차원"도 이름
_NUMBER = re.compile(_EDGE_BEFORE + r"\d+(?:[.,]\d+)*" + _EDGE_AFTER)


def unverified_numbers(text: str, sources: list[str]) -> list[str]:
    """text에 나온 수치 중 sources 어디에도 (홀로 선 숫자로) 나오지 않는 것."""
    # 코드 속 정규식(192\.168)이나 문자열 이스케이프 때문에 못 찾는 일이 없도록 역슬래시는 무시
    sources = [src.replace("\\", "") for src in sources]
    missing = []
    for num in dict.fromkeys(_NUMBER.findall(text)):
        variants = {num, num.replace(",", "")}
        patterns = [re.compile(_EDGE_BEFORE + re.escape(v) + _EDGE_AFTER) for v in variants]
        if any(p.search(src) for p in patterns for src in sources):
            continue
        if _parts_found(num, sources):
            continue
        missing.append(num)
    return missing


def _parts_found(num: str, sources: list[str]) -> bool:
    """IP 같은 점 숫자(192.168)는 코드에 a === 192 && b === 168처럼 나뉘어 있기도 하다.
    모든 조각이 두 자리 이상이고 한 커밋 안에 각각 홀로 나오면 확인된 것으로 본다.
    (한 자리 조각까지 허용하면 "2.5" 같은 소수가 너무 쉽게 통과하므로 제외)"""
    parts = num.split(".")
    if len(parts) < 2 or any(len(p) < 2 for p in parts):
        return False
    patterns = [re.compile(_EDGE_BEFORE + re.escape(p) + _EDGE_AFTER) for p in parts]
    return any(all(p.search(src) for p in patterns) for src in sources)


def validate_outputs(
    raw: LLMOutputs,
    commits: list[Commit],
    index: CommitIndex,
    repo: RepoInfo,
    notes: list[str],
    groups: list[list[str]] | None = None,
) -> Outputs:
    sources = {c.sha: commit_source_text(c) for c in commits}
    relevance = RelevanceIndex(commits, groups)
    readme_text = "\n".join(filter(None, [repo.readme, repo.description, repo.name]))
    everything = list(sources.values()) + [readme_text]

    def resolve(refs: list[str], where: str) -> tuple[list[str], bool]:
        """근거 목록 → (커밋 SHA들, README 근거 여부). 없는 ID는 메모를 남기고 뺀다."""
        shas: list[str] = []
        from_readme = False
        for ref in refs:
            if ref.strip().upper() == "README":
                if readme_text:
                    from_readme = True
                else:
                    notes.append(f"{where}: README가 없는데 README를 근거로 달아 뺐습니다.")
                continue
            sha = index.sha_of(ref)
            if sha is None:
                notes.append(f"{where}: 없는 커밋 ID {ref!r}를 근거에서 뺐습니다.")
            elif sha not in shas:
                shas.append(sha)
        return shas, from_readme

    def evidence_text(shas: list[str], from_readme: bool) -> list[str]:
        return [sources[s] for s in shas] + ([readme_text] if from_readme else [])

    def statement(text: str, refs: list[str], where: str) -> Statement | None:
        shas, from_readme = resolve(refs, where)
        if not shas and not from_readme:
            notes.append(f"{where}: 근거가 없어 문장을 뺐습니다 → {text}")
            return None
        # 숫자는 AI가 처음 단 근거로 확인한다. 근거를 고친 뒤에 확인하면 잘못된 근거에 기대
        # 쓴 문장이 다른 커밋의 숫자로 통과될 수 있어서다.
        missing = unverified_numbers(text, evidence_text(shas, from_readme))
        if missing:
            # 근거와 맞지 않는 숫자가 든 문장은 경고만 붙이지 않고 뺀다 (지어낸 수치일 수 있으므로)
            notes.append(f"{where}: 숫자 {', '.join(missing)}이(가) 근거 커밋에서 확인되지 않아 문장을 뺐습니다 → {text}")
            return None
        check = relevance.check_evidence(text, shas)
        notes.extend(f"{where}: {n} → {text}" for n in check.notes)
        warnings = [check.warning] if check.warning else []
        return Statement(text=text, evidence=check.evidence, from_readme=from_readme, warnings=warnings)

    def check_free_text(text: str, where: str) -> None:
        """근거가 따로 없는 글(개요, 발표자 메모 등)은 레포 전체에서 숫자를 찾는다."""
        missing = unverified_numbers(text, everything)
        if missing:
            notes.append(f"{where}: 숫자 {', '.join(missing)}이(가) README·커밋에서 확인되지 않습니다.")

    # ---- 포트폴리오
    p = raw.portfolio
    check_free_text(p.tagline + " " + p.overview, "포트폴리오 개요")
    contributions: list[Contribution] = []
    for i, c in enumerate(p.contributions, 1):
        where = f"포트폴리오 기여 {i}번 '{c.title}'"
        summary = statement(c.summary.text, c.summary.evidence, where)
        points = [s for pt in c.points if (s := statement(pt.text, pt.evidence, where))]
        if summary is None and not points:
            notes.append(f"{where}: 남은 문장이 없어 기여 전체를 뺐습니다.")
            continue
        if summary is None:  # 요약 문장만 근거가 없으면 첫 포인트를 요약으로 올린다
            summary, points = points[0], points[1:]
        contributions.append(Contribution(title=c.title, summary=summary, points=points, technologies=c.technologies))

    # ---- 슬라이드
    slides: list[Slide] = []
    for i, sl in enumerate(raw.slides, 1):
        where = f"슬라이드 {i}장 '{sl.title}'"
        check_free_text(sl.headline, where + " 핵심 메시지")
        check_free_text(sl.notes, where + " 발표자 메모")
        points = []
        for pt in sl.points:
            st = statement(f"{pt.heading} {pt.text}", pt.evidence, where)
            if st:
                points.append(SlidePoint(heading=pt.heading, **{**st.model_dump(), "text": pt.text}))
        highlights = []
        for h in sl.highlights:
            # 큰 숫자 카드는 눈에 잘 띄므로 경고 대신 아예 뺀다
            shas, from_readme = resolve(h.evidence, where)
            if (shas or from_readme) and not unverified_numbers(h.value, evidence_text(shas, from_readme)):
                highlights.append(Highlight(value=h.value, label=h.label, evidence=shas, from_readme=from_readme))
            else:
                notes.append(f"{where}: 근거에서 확인되지 않는 수치 카드를 뺐습니다 → {h.value} {h.label}")
        if sl.points and not points and sl.layout != "cover":
            notes.append(f"{where}: 남은 항목이 없어 장 전체를 뺐습니다.")
            continue
        slides.append(
            Slide(layout=sl.layout, title=sl.title, headline=sl.headline, points=points,
                  highlights=highlights, flow=sl.flow, notes=sl.notes)
        )

    return Outputs(
        portfolio=Portfolio(
            tagline=p.tagline,
            overview=p.overview,
            contributions=contributions,
            tech_stack=[TechGroup(category=g.category, items=g.items) for g in p.tech_stack if g.items],
        ),
        slides=slides,
    )
