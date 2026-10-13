"""4-3단계: LLM 출력 검증.

프롬프트로 "지어내지 마라"고 해도 100% 지켜지지는 않는다. 그래서 코드로 한 번 더 거른다.
- 근거 커밋 ID가 실제로 있는지 (없는 ID는 빼고, 근거가 하나도 안 남은 문장은 버린다)
- "README" 근거는 README나 레포 설명이 실제로 있을 때만 인정
- 문장 속 숫자가 근거(커밋 메시지·diff, README)에 실제로 나오는지 (안 나오면 경고 표시)
"""

import re

from app.models import Commit, Outputs, Portfolio, RepoInfo, Slide, Statement
from app.pipeline.generate import LLMOutputs, LLMStatement
from app.pipeline.summarize import commit_source_text
from app.pipeline.text import CommitIndex

# 홀로 선 숫자만 본다: "19종", "30%", "retry(5)"의 숫자는 잡고, "3D", "v1.3", "i18n", "SHA-256"처럼
# 영문·숫자와 붙어 이름의 일부인 숫자는 수치가 아니므로 무시한다.
_EDGE_BEFORE = r"(?<![0-9A-Za-z.,])(?<![A-Za-z]-)"
_EDGE_AFTER = r"(?![0-9A-Za-z]|[.,]\d)"
_NUMBER = re.compile(_EDGE_BEFORE + r"\d+(?:[.,]\d+)*" + _EDGE_AFTER)


def unverified_numbers(text: str, sources: list[str]) -> list[str]:
    """text에 나온 수치 중 sources 어디에도 (홀로 선 숫자로) 나오지 않는 것."""
    missing = []
    for num in dict.fromkeys(_NUMBER.findall(text)):
        variants = {num, num.replace(",", "")}
        patterns = [re.compile(_EDGE_BEFORE + re.escape(v) + _EDGE_AFTER) for v in variants]
        if not any(p.search(src) for p in patterns for src in sources):
            missing.append(num)
    return missing


def validate_outputs(
    raw: LLMOutputs,
    commits: list[Commit],
    index: CommitIndex,
    repo: RepoInfo,
    notes: list[str],
) -> Outputs:
    sources = {c.sha: commit_source_text(c) for c in commits}
    readme_text = "\n".join(filter(None, [repo.readme, repo.description, repo.name]))

    def convert(stmt: LLMStatement, where: str) -> Statement | None:
        shas: list[str] = []
        from_readme = False
        for ref in stmt.evidence:
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
        if not shas and not from_readme:
            notes.append(f"{where}: 근거가 없어 문장을 뺐습니다 → {stmt.text}")
            return None
        evidence_text = [sources[s] for s in shas] + ([readme_text] if from_readme else [])
        warnings = [
            f"숫자 '{n}'이(가) 근거에서 확인되지 않습니다" for n in unverified_numbers(stmt.text, evidence_text)
        ]
        return Statement(text=stmt.text, evidence=shas, from_readme=from_readme, warnings=warnings)

    p = raw.portfolio
    contributions = [s for i, c in enumerate(p.contributions, 1) if (s := convert(c, f"포트폴리오 기여 {i}번"))]
    overview_missing = unverified_numbers(p.overview, list(sources.values()) + [readme_text])
    if overview_missing:
        notes.append(f"포트폴리오 개요: 숫자 {', '.join(overview_missing)}이(가) README·커밋에서 확인되지 않습니다.")

    slides = []
    for i, slide in enumerate(raw.slides, 1):
        bullets = [s for b in slide.bullets if (s := convert(b, f"슬라이드 {i}장"))]
        notes_missing = unverified_numbers(slide.notes, list(sources.values()) + [readme_text])
        if notes_missing:
            notes.append(f"슬라이드 {i}장 발표자 메모: 숫자 {', '.join(notes_missing)}이(가) 근거에서 확인되지 않습니다.")
        if not bullets and slide.bullets:
            notes.append(f"슬라이드 {i}장 '{slide.title}': 남은 문장이 없어 장 전체를 뺐습니다.")
            continue
        slides.append(Slide(title=slide.title, bullets=bullets, notes=slide.notes))

    return Outputs(
        portfolio=Portfolio(overview=p.overview, contributions=contributions, tech_stack=p.tech_stack),
        slides=slides,
    )
