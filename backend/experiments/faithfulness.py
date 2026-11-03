"""실험 1. 근거 정확도: 기준선 LLM vs CommitFolio(검증 전) vs CommitFolio(최종)

같은 레포로 세 조건의 포트폴리오 문장을 만들고, 문장마다 "근거 커밋이 이 문장을 뒷받침하는가"를 잰다.
  A 기준선   README + 커밋 목록을 주고 "포트폴리오 써 줘" (보통 사람이 LLM을 쓰는 방식)
  B 검증 전  CommitFolio 파이프라인(그룹화 → diff 요약 → 생성)까지, 코드 검증은 하기 전
  C 최종     B에 코드 검증(근거 ID·숫자·인용·일치도)까지 마친 결과
A·B는 같은 생성 모델(Gemini)을 써서 차이가 '과정'에서만 나도록 했다.
판정은 다른 회사 모델(Claude)이 하고, 세 조건의 문장을 섞어서 보여 줘 어느 조건인지 모르게 한다.

실행 (backend 폴더에서):
  uv run python -m experiments.faithfulness                 # 전체 레포
  uv run python -m experiments.faithfulness --repo DeskBoard # 하나만
  uv run python -m experiments.faithfulness --human results/human_check.csv  # 사람 판정과 일치도
결과: experiments/results/faithfulness.md, .json, human_check.csv
같은 입력의 AI 응답은 캐시되므로, 하루 한도에 걸려 멈춰도 다음 날 다시 실행하면 이어서 진행된다.
"""

import argparse
import csv
import json
import random
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.config import get_settings
from app.github.collector import collect
from app.models import Commit, Outputs
from app.pipeline.generate import LLMOutputs, LLMPortfolio, LLMStatement, generate_outputs
from app.pipeline.grouping.heuristic import HeuristicGrouper
from app.pipeline.llm import LLMCache, make_llm
from app.pipeline.summarize import commit_source_text, summarize_groups
from app.pipeline.text import CommitIndex, strip_trailers
from app.pipeline.validate import unverified_numbers, validate_outputs
from experiments.metrics import cohen_kappa

# 언어가 서로 다른 6개 레포. 커밋이 너무 많은 레포는 기간(since)으로 50~150개 정도로 맞췄다
REPOS = [
    {"url": "dgim9390/DeskBoard", "user": "dgim9390"},
    {"url": "dgim9390/commitfolio", "user": "dgim9390"},
    {"url": "pomber/git-history", "user": "pomber"},
    {"url": "nalgeon/sqlean", "user": "nalgeon", "since": "2025-11-01"},
    {"url": "sharkdp/hyperfine", "user": "sharkdp", "since": "2026-05-01"},
    {"url": "simonw/llm", "user": "simonw", "since": "2026-08-01"},
]
RESULTS = Path(__file__).parent / "results"
CONDITIONS = {"A": "기준선 LLM", "B": "CommitFolio 검증 전", "C": "CommitFolio 최종"}
JUDGE_BATCH = 25  # 판정 한 번에 보낼 문장 수 (근거 diff가 길어지지 않게)
EVIDENCE_CHARS = 2500  # 판정자에게 보여줄 커밋 하나의 원문 길이

BASELINE_PROMPT = """다음은 내 GitHub 프로젝트의 README와 내가 작성한 커밋 목록이야.
이력서·포트폴리오에 넣을 소개글을 써 줘. 주요 기여 4~6개, 기여마다 배경·한 일·구현 포인트·결과를 쓰고,
문장마다 근거가 된 커밋 ID(C01 형식)를 붙여 줘.

{input}"""


# ---------------------------------------------------------------- 판정자 형식


class Verdict(BaseModel):
    id: int
    verdict: Literal["supported", "partial", "unsupported"]
    reason: str


class JudgeBatch(BaseModel):
    verdicts: list[Verdict]


JUDGE_SYSTEM = """너는 개발자 포트폴리오 문장이 실제 커밋으로 뒷받침되는지 검사하는 엄격한 심사자다.
각 문장과, 그 문장이 근거로 든 커밋들의 메시지·변경 파일·diff가 주어진다. 문장마다 하나로 판정하라.
- supported: 문장의 구체적인 내용(무엇을 만들었는지, 쓴 기술, 숫자, 이유·효과)이 모두 근거 커밋에서 확인된다
- partial: 핵심 내용은 확인되지만 일부 세부(숫자, 이유, 효과 등)는 근거에서 확인되지 않는다
- unsupported: 핵심 내용이 근거 커밋에서 확인되지 않거나 근거와 어긋난다
근거에 없는 내용은 그럴듯해도 확인된 것으로 치지 마라. reason은 한 문장으로."""


# ---------------------------------------------------------------- 문장 모으기


@dataclass
class Item:
    condition: str
    text: str
    shas: list[str]  # 유효한 근거 커밋
    bad_ids: int = 0  # 없는 커밋 ID를 단 개수
    verdict: str | None = None
    reason: str = ""


@dataclass
class RepoRun:
    name: str
    commits: dict[str, Commit]
    items: list[Item] = field(default_factory=list)


def statements_of_raw(portfolio: LLMPortfolio) -> list[LLMStatement]:
    out = []
    for c in portfolio.contributions:
        out += [s for s in (c.background, c.summary, *c.points, c.outcome) if s and s.text.strip()]
    return out


def items_from_raw(condition: str, portfolio: LLMPortfolio, index: CommitIndex) -> list[Item]:
    items = []
    for s in statements_of_raw(portfolio):
        shas = [sha for ref in s.evidence if (sha := index.sha_of(ref))]
        bad = sum(1 for ref in s.evidence if ref.strip().upper() != "README" and not index.sha_of(ref))
        items.append(Item(condition, s.text, list(dict.fromkeys(shas)), bad))
    return items


def items_from_final(outputs: Outputs) -> list[Item]:
    items = []
    for c in outputs.portfolio.contributions:
        for s in (c.background, c.summary, *c.points, c.outcome):
            if s and s.text.strip():
                items.append(Item("C", s.text, list(s.evidence)))
    return items


def baseline_input(run_commits: list[Commit], index: CommitIndex, readme: str | None) -> str:
    lines = [f"# README\n{(readme or '-')[:6000]}", "\n# 커밋 목록"]
    for c in run_commits:
        files = ", ".join(f.path for f in c.files[:5])
        lines.append(f"{index.id_of(c.sha)} {c.authored_at:%Y-%m-%d} {strip_trailers(c.message)[:300]} [{files}]")
    return "\n".join(lines)


def run_repo(spec: dict, settings, gen_llm) -> RepoRun:
    since = date.fromisoformat(spec["since"]) if spec.get("since") else None
    print(f"\n▶ {spec['url']} 수집·그룹화")
    collected = collect(spec["url"], spec["user"], since, None, settings)
    grouping = HeuristicGrouper().group(collected.commits)
    by_sha = {c.sha: c for c in collected.commits}
    analyzed = [by_sha[s] for g in grouping.groups for s in g.commit_shas]
    index = CommitIndex(analyzed)
    print(f"  커밋 {len(analyzed)}개 · 작업 {len(grouping.groups)}개")

    run = RepoRun(spec["url"], {c.sha: c for c in analyzed})
    # A 기준선 (README + 커밋 목록, 검증 규칙 없는 평범한 요청)
    baseline = gen_llm.parse(
        system="너는 개발자를 돕는 어시스턴트다.",
        prompt=BASELINE_PROMPT.format(input=baseline_input(analyzed, index, collected.repo.readme)),
        schema=LLMPortfolio,
    )
    run.items += items_from_raw("A", baseline, index)
    # B·C CommitFolio
    notes: list[str] = []
    summaries = summarize_groups(collected, grouping, index, gen_llm, settings, notes)
    raw: LLMOutputs = generate_outputs(collected, summaries, index, gen_llm, settings)
    run.items += items_from_raw("B", raw.portfolio, index)
    final = validate_outputs(raw, analyzed, index, collected.repo, notes, [g.commit_shas for g in grouping.groups])
    run.items += items_from_final(final)
    return run


# ---------------------------------------------------------------- 판정


def judge_repo(run: RepoRun, judge_llm, seed: int = 0) -> None:
    # 같은 문장·근거는 한 번만 판정하고, 조건을 섞어서 보낸다 (어느 조건 문장인지 모르게)
    unique: dict[tuple, list[Item]] = {}
    for it in run.items:
        if not it.shas:
            it.verdict, it.reason = "unsupported", "유효한 근거 커밋이 없음"
            continue
        unique.setdefault((it.text, tuple(it.shas)), []).append(it)
    keys = list(unique)
    random.Random(seed).shuffle(keys)

    for start in range(0, len(keys), JUDGE_BATCH):
        batch = keys[start : start + JUDGE_BATCH]
        cited = list(dict.fromkeys(sha for _, shas in batch for sha in shas))
        evidence = "\n\n".join(
            f"## 커밋 {sha[:7]}\n{commit_source_text(run.commits[sha])[:EVIDENCE_CHARS]}" for sha in cited
        )
        statements = "\n".join(
            f"[{i}] {text} (근거: {', '.join(s[:7] for s in shas)})" for i, (text, shas) in enumerate(batch)
        )
        result = judge_llm.parse(
            system=JUDGE_SYSTEM,
            prompt=f"# 근거 커밋\n{evidence}\n\n# 판정할 문장\n{statements}",
            schema=JudgeBatch,
        )
        for v in result.verdicts:
            if 0 <= v.id < len(batch):
                for it in unique[batch[v.id]]:
                    it.verdict, it.reason = v.verdict, v.reason
    missing = sum(1 for it in run.items if it.verdict is None)
    if missing:
        print(f"  ⚠ 판정 응답에서 빠진 문장 {missing}개 (집계에서 제외)")


# ---------------------------------------------------------------- 집계


_NUM = re.compile(r"\d")


def summarize_condition(runs: list[RepoRun], cond: str) -> dict:
    items = [it for r in runs for it in r.items if it.condition == cond]
    judged = [it for it in items if it.verdict]
    with_numbers = [(r, it) for r in runs for it in r.items if it.condition == cond and _NUM.search(it.text)]
    numbers_ok = sum(
        1
        for r, it in with_numbers
        if it.shas and not unverified_numbers(it.text, [commit_source_text(r.commits[s]) for s in it.shas])
    )
    share = lambda v: sum(it.verdict == v for it in judged) / len(judged) if judged else 0.0  # noqa: E731
    return {
        "condition": CONDITIONS[cond],
        "statements": len(items),
        "bad_id_rate": sum(it.bad_ids > 0 for it in items) / len(items) if items else 0.0,
        "no_evidence_rate": sum(not it.shas for it in items) / len(items) if items else 0.0,
        "number_ok_rate": numbers_ok / len(with_numbers) if with_numbers else None,
        "with_numbers": len(with_numbers),
        "supported": share("supported"),
        "partial": share("partial"),
        "unsupported": share("unsupported"),
    }


def pct(x) -> str:
    return "-" if x is None else f"{x * 100:.0f}%"


def write_report(runs: list[RepoRun], judge_model: str) -> None:
    RESULTS.mkdir(exist_ok=True)
    rows = {c: summarize_condition(runs, c) for c in CONDITIONS}
    per_repo = {r.name: {c: summarize_condition([r], c) for c in CONDITIONS} for r in runs}
    lines = [
        "# 실험 1. 근거 정확도",
        "",
        f"레포 {len(runs)}개 · 판정자 {judge_model} (세 조건의 문장을 섞어 블라인드 판정)",
        "",
        "| 조건 | 문장 수 | 뒷받침됨 | 일부만 | 근거 없음 | 없는 커밋 ID | 숫자 확인됨 |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows.values():
        lines.append(
            f"| {r['condition']} | {r['statements']} | {pct(r['supported'])} | {pct(r['partial'])} | "
            f"{pct(r['unsupported'])} | {pct(r['bad_id_rate'])} | {pct(r['number_ok_rate'])} ({r['with_numbers']}문장) |"
        )
    lines += ["", "## 레포별 '뒷받침됨' 비율", "", "| 레포 | A 기준선 | B 검증 전 | C 최종 |", "|---|---|---|---|"]
    for name, conds in per_repo.items():
        lines.append(f"| {name} | " + " | ".join(pct(conds[c]["supported"]) for c in CONDITIONS) + " |")
    (RESULTS / "faithfulness.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (RESULTS / "faithfulness.json").write_text(
        json.dumps(
            {
                "judge": judge_model,
                "summary": rows,
                "per_repo": per_repo,
                "items": [{"repo": r.name, **it.__dict__} for r in runs for it in r.items],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("\n" + "\n".join(lines))


def export_human_check(runs: list[RepoRun], n: int = 20, seed: int = 1) -> None:
    """사람이 판정자 결과를 확인할 표본. 판정자 답은 따로 두어 사람이 보지 않고 판정하게 한다."""
    pool = [(r, it) for r in runs for it in r.items if it.verdict and it.shas]
    sample = random.Random(seed).sample(pool, min(n, len(pool)))
    with open(RESULTS / "human_check.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["no", "repo", "statement", "evidence_urls", "human_verdict (supported/partial/unsupported)"])
        for i, (r, it) in enumerate(sample, 1):
            urls = " ".join(r.commits[s].url for s in it.shas)
            w.writerow([i, r.name, it.text, urls, ""])
    (RESULTS / "human_check_key.json").write_text(
        json.dumps([it.verdict for _, it in sample], ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n사람 확인용 표본 {len(sample)}개: {RESULTS / 'human_check.csv'}")


def compare_human(path: Path) -> None:
    with open(path, encoding="utf-8-sig") as f:
        human = [row[4].strip() for row in list(csv.reader(f))[1:]]
    judge = json.loads((RESULTS / "human_check_key.json").read_text(encoding="utf-8"))
    pairs = [(h, j) for h, j in zip(human, judge) if h]
    if not pairs:
        print("human_verdict 칸이 비어 있습니다.")
        return
    agree = sum(h == j for h, j in pairs) / len(pairs)
    kappa = cohen_kappa([h for h, _ in pairs], [j for _, j in pairs])
    print(f"사람 {len(pairs)}개 판정 · 일치율 {agree * 100:.0f}% · Cohen's kappa {kappa:.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", help="레포 이름 일부 (예: DeskBoard). 없으면 전체")
    ap.add_argument("--judge-model", default="claude-opus-5-5")
    ap.add_argument("--human", type=Path, help="채운 human_check.csv로 사람-판정자 일치도 계산")
    ap.add_argument("--generate-only", action="store_true", help="판정 없이 A·B·C 문장만 만들어 캐시에 저장 (Claude 키 없이 가능)")
    args = ap.parse_args()
    if args.human:
        compare_human(args.human)
        return

    settings = get_settings()
    cache = LLMCache(settings.cache_dir / "llm.sqlite3")
    gen_llm = make_llm(settings, cache)
    judge_llm = make_llm(settings.model_copy(update={"llm_provider": "claude", "llm_model": args.judge_model}), cache)

    runs = []
    for spec in REPOS:
        if args.repo and args.repo.lower() not in spec["url"].lower():
            continue
        run = run_repo(spec, settings, gen_llm)
        counts = {c: sum(it.condition == c for it in run.items) for c in CONDITIONS}
        print(f"  문장 수 A {counts['A']} · B {counts['B']} · C {counts['C']}")
        if not args.generate_only:
            judge_repo(run, judge_llm)
        runs.append(run)
    if args.generate_only:
        print(f"\n생성 모델 {gen_llm.usage.model}: 호출 {gen_llm.usage.calls}회 (캐시 {gen_llm.usage.cached_calls})")
        return
    write_report(runs, args.judge_model)
    export_human_check(runs)
    print(f"\n생성 모델 {gen_llm.usage.model}: 호출 {gen_llm.usage.calls}회 (캐시 {gen_llm.usage.cached_calls})")
    print(f"판정 모델 {judge_llm.usage.model}: 호출 {judge_llm.usage.calls}회, 입력 {judge_llm.usage.input_tokens:,} · 출력 {judge_llm.usage.output_tokens:,} 토큰")


if __name__ == "__main__":
    main()
