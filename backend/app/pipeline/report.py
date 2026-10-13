"""AnalysisResult → 사람이 읽는 마크다운 (CLI 출력·파일 저장용)."""

from app.models import AnalysisResult, Statement
from app.pipeline.grouping.rules import EXCLUDE_LABELS


def render_markdown(r: AnalysisResult) -> str:
    urls = {c.sha: c.url for c in r.commits}
    titles = {c.sha: c.title for c in r.commits}

    def evidence(s: Statement) -> str:
        refs = [f"[`{sha[:7]}`]({urls[sha]})" for sha in s.evidence]
        if s.from_readme:
            refs.append(f"[README]({r.repo.url}#readme)")
        warn = "".join(f"\n  - ⚠️ {w}" for w in s.warnings)
        return f"{s.text}  \n  근거: {' '.join(refs)}{warn}"

    period = f"{r.since or '처음'} ~ {r.until or '현재'}"
    out = [f"# {r.repo.owner}/{r.repo.name} · {r.username} · {period}", ""]

    p = r.outputs.portfolio
    out += ["## 포트폴리오 소개글", "", "### 프로젝트 개요", "", p.overview or "(없음)", "", "### 주요 기여", ""]
    out += [f"- {evidence(s)}" for s in p.contributions] or ["(없음)"]
    out += ["", "### 기술 스택", "", ", ".join(p.tech_stack) or "-", ""]

    out += ["## 발표 자료", ""]
    for i, slide in enumerate(r.outputs.slides, 1):
        out += [f"### {i}. {slide.title}", ""]
        out += [f"- {evidence(s)}" for s in slide.bullets]
        if slide.notes:
            out += ["", f"> 발표자 메모: {slide.notes}"]
        out.append("")

    out += ["---", "", "## 참고: 작업 요약", ""]
    for s in r.summaries:
        out += [f"**{s.group_id}. {s.title}** ({s.significance}) — {s.solution}", ""]
    if r.grouping.excluded:
        out.append("분석 제외 커밋: " + ", ".join(
            f"`{e.sha[:7]}` {titles[e.sha]} ({EXCLUDE_LABELS.get(e.reason, e.reason)})" for e in r.grouping.excluded
        ))
        out.append("")
    if r.validation_notes:
        out += ["### 검증 메모", ""] + [f"- {n}" for n in r.validation_notes] + [""]
    u = r.usage
    cost = f", 약 ${u.estimated_cost_usd:.2f}" if u.estimated_cost_usd is not None else ""
    out.append(f"_{u.model} · API 호출 {u.calls}회 (캐시 {u.cached_calls}회) · 입력 {u.input_tokens:,} / 출력 {u.output_tokens:,} 토큰{cost}_")
    return "\n".join(out)
