"""실험 2. 그룹화 품질: 사람이 직접 묶은 정답과 비교

1) 정답 표 만들기 → label 칸에 작업 이름을 적는다 (같은 작업이면 같은 이름)
   uv run python -m experiments.grouping export dgim9390/DeskBoard dgim9390
2) 평가
   uv run python -m experiments.grouping evaluate experiments/labels/DeskBoard.csv dgim9390/DeskBoard dgim9390

비교하는 방법
  CommitFolio        지금 방식 (같은 PR·이름표 규칙 + 유사도 평균 연결)
  이름표 규칙 끔     메시지 이름표("3D:") 규칙을 뺀 것 → 규칙의 효과
  단일 연결          같은 점수·같은 기준값이지만 한 쌍만 비슷해도 합치는 방식 → '사슬 현상'의 효과
  시간 간격(12시간)  12시간 넘게 쉬면 새 작업으로 보는 단순한 방법
  커밋마다 따로      참고용 하한선
기준값(0.3)은 DeskBoard로 조정했으므로, 다른 레포 결과가 '조정하지 않은' 성능이다.
"""

import argparse
import csv
import math
from pathlib import Path

from app.config import get_settings
from app.github.collector import collect, parse_repo_url
from app.models import Commit
from app.pipeline.grouping.base import UnionFind
from app.pipeline.grouping.heuristic import HeuristicConfig, HeuristicGrouper, idf, message_tokens, path_features, similarity
from experiments.metrics import ari, nmi

LABELS = Path(__file__).parent / "labels"


def kept_commits(repo: str, user: str) -> tuple[list[Commit], list[list[str]]]:
    """CommitFolio가 분석 대상으로 남기는 커밋(문서·버전 커밋 제외)과 그 그룹."""
    collected = collect(repo, user, None, None, get_settings())
    grouping = HeuristicGrouper().group(collected.commits)
    by_sha = {c.sha: c for c in collected.commits}
    kept = sorted((by_sha[s] for g in grouping.groups for s in g.commit_shas), key=lambda c: c.authored_at)
    return kept, [g.commit_shas for g in grouping.groups]


def export(repo: str, user: str) -> None:
    commits, _ = kept_commits(repo, user)
    LABELS.mkdir(exist_ok=True)
    path = LABELS / f"{parse_repo_url(repo)[1]}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["sha", "date", "title", "files", "label"])
        for c in commits:
            files = ", ".join(x.path for x in c.included_files[:4])
            w.writerow([c.sha[:7], f"{c.authored_at.astimezone():%Y-%m-%d %H:%M}", c.title, files, ""])
    print(f"정답 표 {len(commits)}행: {path}\nlabel 칸에 작업 이름을 적어 주세요 (같은 작업이면 같은 이름).")


# ---------------------------------------------------------------- 비교 방법들 (커밋 → 그룹 번호)


def as_labels(groups: list[list[str]], commits: list[Commit]) -> list[int]:
    of = {sha: i for i, g in enumerate(groups) for sha in g}
    return [of[c.sha] for c in commits]


def single_linkage(commits: list[Commit], cfg: HeuristicConfig) -> list[int]:
    files = [path_features(c) for c in commits]
    msgs = [message_tokens(c.message) for c in commits]
    fw, mw = idf(files), idf(msgs)
    uf = UnionFind(len(commits))
    for i in range(len(commits)):
        for j in range(i + 1, len(commits)):
            hours = abs((commits[j].authored_at - commits[i].authored_at).total_seconds()) / 3600
            score = (
                cfg.w_files * similarity(files[i], files[j], fw)
                + cfg.w_msg * similarity(msgs[i], msgs[j], mw)
                + cfg.w_time * math.exp(-hours / cfg.time_scale_hours)
            )
            if score >= cfg.threshold:
                uf.union(i, j)
    return [uf.find(i) for i in range(len(commits))]


def time_gap(commits: list[Commit], hours: float = 12) -> list[int]:
    labels, group = [], 0
    for prev, cur in zip([None, *commits], commits):
        if prev and (cur.authored_at - prev.authored_at).total_seconds() > hours * 3600:
            group += 1
        labels.append(group)
    return labels


def evaluate(path: Path, repo: str, user: str) -> None:
    commits, groups = kept_commits(repo, user)
    with open(path, encoding="utf-8-sig") as f:
        truth_by_sha = {row["sha"]: row["label"].strip() for row in csv.DictReader(f)}
    missing = [c.sha[:7] for c in commits if not truth_by_sha.get(c.sha[:7])]
    if missing:
        raise SystemExit(f"label이 비어 있는 커밋 {len(missing)}개: {', '.join(missing[:10])} ...")
    truth = [truth_by_sha[c.sha[:7]] for c in commits]

    no_labels = HeuristicGrouper(HeuristicConfig(use_message_labels=False)).group(commits)
    methods = {
        "CommitFolio": as_labels(groups, commits),
        "이름표 규칙 끔": as_labels([g.commit_shas for g in no_labels.groups], commits),
        "단일 연결": single_linkage(commits, HeuristicConfig()),
        "시간 간격(12시간)": time_gap(commits),
        "커밋마다 따로": list(range(len(commits))),
    }
    print(f"\n{repo} · 커밋 {len(commits)}개 · 정답 작업 {len(set(truth))}개\n")
    print("| 방법 | 그룹 수 | ARI | NMI |\n|---|---|---|---|")
    for name, labels in methods.items():
        print(f"| {name} | {len(set(labels))} | {ari(truth, labels):.3f} | {nmi(truth, labels):.3f} |")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("repo")
    e.add_argument("user")
    v = sub.add_parser("evaluate")
    v.add_argument("labels", type=Path)
    v.add_argument("repo")
    v.add_argument("user")
    args = ap.parse_args()
    if args.cmd == "export":
        export(args.repo, args.user)
    else:
        evaluate(args.labels, args.repo, args.user)


if __name__ == "__main__":
    main()
