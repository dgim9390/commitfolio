"""규칙 + 유사도 기반 그룹화.

묶는 기준 (사용자가 정한 것)
  0. 분석 제외: 문서만 바꾼 커밋, 버전 번호만 올린 커밋, 분석할 파일이 없는 커밋  → rules.py
  1. 무조건 같은 그룹: 같은 PR, 같은 메시지 이름표("3D: ...", "[auth] ...")         → rules.py
  2. 내용이 비슷하면 같은 그룹: 바꾼 경로와 메시지가 비슷한 정도로 판단 (시간 제한 없음)
  3. 그룹 단위는 '큰 기능'. 다만 한 그룹이 너무 커지면 시간 간격이 가장 큰 곳에서 자른다

2번의 구현
  점수 = w_files·경로유사도 + w_msg·메시지유사도 + w_time·시간근접도(아주 약하게)
  평균 연결(average-linkage) 병합 군집화: 두 그룹 사이 '모든 커밋 쌍의 평균 점수'가 가장 높은
  쌍부터 합치고, threshold 아래면 멈춘다.
  단일 연결(Union-Find로 한 쌍만 비슷해도 합치기)은 A~B, B~C, C~D가 각각 비슷하면 A와 D까지
  묶이는 '사슬 현상'이 생겨서 쓰지 않는다.

유사도에는 IDF 가중치를 쓴다. 'components/'처럼 거의 모든 커밋에 등장하는 경로·단어는
가중치가 0에 가까워져서, 흔한 폴더를 같이 건드렸다는 이유만으로 묶이지 않는다.
"""

import heapq
import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import PurePosixPath

from app.models import Commit, ExcludedCommit, GroupingResult, GroupLink, WorkGroup
from app.pipeline.grouping.base import UnionFind
from app.pipeline.grouping.rules import exclusion_reason, is_doc_file, message_label


@dataclass
class HeuristicConfig:
    # 기준 0, 1 켜고 끄기
    exclude_minor_commits: bool = True
    use_message_labels: bool = True
    # 기준 2: 점수 가중치와 합치는 기준
    w_files: float = 0.6
    w_msg: float = 0.3
    w_time: float = 0.1  # 시간 제한은 없고, 비슷한 점수일 때 가까운 쪽을 살짝 우선하는 정도
    time_scale_hours: float = 24 * 7
    threshold: float = 0.3  # DeskBoard로 조정: 0.25면 리브랜딩이 맥 앱 그룹에 흡수되고, 0.35면 앱 아이콘 커밋이 맥 앱 그룹에서 떨어짐
    # 기준 3
    max_group_size: int = 15
    # 커밋이 이보다 많으면 모든 쌍 대신 시간순 이웃 window개와만 비교 (O(n²) 방지)
    all_pairs_limit: int = 1000
    window: int = 200


class HeuristicGrouper:
    def __init__(self, config: HeuristicConfig | None = None):
        self.cfg = config or HeuristicConfig()

    def group(self, commits: list[Commit]) -> GroupingResult:
        cfg = self.cfg
        commits = sorted((c for c in commits if not c.is_merge), key=lambda c: c.authored_at)

        # 기준 0: 분석 제외
        excluded: list[ExcludedCommit] = []
        if cfg.exclude_minor_commits:
            kept = []
            for c in commits:
                reason = exclusion_reason(c)
                if reason:
                    excluded.append(ExcludedCommit(sha=c.sha, reason=reason))
                else:
                    kept.append(c)
            commits = kept

        n = len(commits)
        if n == 0:
            return GroupingResult(groups=[], excluded=excluded)

        file_feats = [path_features(c) for c in commits]
        msg_feats = [message_tokens(c.message) for c in commits]
        file_idf = idf(file_feats)
        msg_idf = idf(msg_feats)

        # 기준 1: 무조건 같은 그룹 (같은 PR, 같은 이름표)
        uf = UnionFind(n)
        forced_links: list[GroupLink] = []
        first_seen: dict[str, int] = {}
        for i, c in enumerate(commits):
            keys = []
            if c.pr_number is not None:
                keys.append((f"pr:{c.pr_number}", f"같은 PR #{c.pr_number}"))
            label = message_label(c.message) if cfg.use_message_labels else None
            if label:
                keys.append((f"label:{label}", f"같은 이름표 '{label}'"))
            for key, reason in keys:
                j = first_seen.setdefault(key, i)
                if j != i and uf.union(j, i):
                    forced_links.append(GroupLink(a=commits[j].sha, b=c.sha, score=1.0, reason=reason))

        # 기준 2: 커밋 쌍 점수
        window = n if n <= cfg.all_pairs_limit else cfg.window
        pair_scores: list[tuple[int, int, float, str]] = []
        for i in range(n):
            for j in range(i + 1, min(n, i + 1 + window)):
                hours = (commits[j].authored_at - commits[i].authored_at).total_seconds() / 3600
                t = math.exp(-hours / cfg.time_scale_hours)
                f = similarity(file_feats[i], file_feats[j], file_idf)
                m = similarity(msg_feats[i], msg_feats[j], msg_idf)
                score = cfg.w_files * f + cfg.w_msg * m + cfg.w_time * t
                if score > 0:
                    pair_scores.append((i, j, score, f"경로 {f:.2f} · 메시지 {m:.2f} · 시간 {t:.2f}"))

        clusters, merge_links = _average_linkage(
            [sorted(comp) for comp in uf.components()], pair_scores, cfg.threshold, commits
        )
        links = forced_links + merge_links

        # 기준 3: 너무 큰 그룹 자르기
        final: list[list[int]] = []
        for members in clusters:
            final.extend(self._split(sorted(members), commits))

        groups = []
        for members in sorted(final, key=lambda m: commits[m[0]].authored_at):
            shas = {commits[i].sha for i in members}
            groups.append(
                WorkGroup(
                    id=len(groups) + 1,
                    commit_shas=[commits[i].sha for i in members],
                    started_at=commits[members[0]].authored_at,
                    ended_at=commits[members[-1]].authored_at,
                    paths=_top_features((file_feats[i] for i in members), file_idf, k=4, dirs_only=True),
                    keywords=_keywords([commits[i] for i in members], msg_idf, k=6),
                    links=[link for link in links if link.a in shas and link.b in shas],
                )
            )
        return GroupingResult(groups=groups, excluded=excluded)

    def _split(self, members: list[int], commits: list[Commit]) -> list[list[int]]:
        if len(members) <= self.cfg.max_group_size:
            return [members]
        gaps = [
            (commits[members[k + 1]].authored_at - commits[members[k]].authored_at, k)
            for k in range(len(members) - 1)
        ]
        _, cut = max(gaps)
        return self._split(members[: cut + 1], commits) + self._split(members[cut + 1 :], commits)


def _average_linkage(
    initial: list[list[int]],
    pair_scores: list[tuple[int, int, float, str]],
    threshold: float,
    commits: list[Commit],
) -> tuple[list[list[int]], list[GroupLink]]:
    """평균 연결 병합 군집화.

    점수가 있는 쌍은 시간 창 안의 것뿐이라 희소하다(약 n·window개). 그래서 n×n 행렬 대신
    '이웃 그룹 쌍 → 점수 합' 사전과 최대 힙을 써서 O(E log E) 정도로 돈다.
    힙에 든 값이 낡았는지(그 사이 그룹이 합쳐졌는지)는 꺼낼 때 다시 계산해 확인한다 (lazy deletion).
    """
    owner: dict[int, int] = {}  # 커밋 → 그룹 id
    members: dict[int, list[int]] = {}
    for cid, comp in enumerate(initial):
        members[cid] = list(comp)
        for i in comp:
            owner[i] = cid

    def key(a: int, b: int) -> tuple[int, int]:
        return (a, b) if a < b else (b, a)

    # 그룹 쌍별 점수 합, 그리고 설명용으로 가장 점수 높은 커밋 쌍
    total: dict[tuple[int, int], float] = {}
    best: dict[tuple[int, int], tuple[float, int, int, str]] = {}
    neighbors: dict[int, set[int]] = {cid: set() for cid in members}
    for i, j, score, reason in pair_scores:
        a, b = owner[i], owner[j]
        if a == b:
            continue
        k = key(a, b)
        total[k] = total.get(k, 0.0) + score
        if k not in best or score > best[k][0]:
            best[k] = (score, i, j, reason)
        neighbors[a].add(b)
        neighbors[b].add(a)

    def average(k: tuple[int, int]) -> float:
        return total[k] / (len(members[k[0]]) * len(members[k[1]]))

    heap = [(-average(k), k) for k in total]
    heapq.heapify(heap)
    links: list[GroupLink] = []

    while heap:
        neg_avg, k = heapq.heappop(heap)
        a, b = k
        if a not in members or b not in members or k not in total:
            continue  # 이미 다른 그룹에 흡수됨
        avg = average(k)
        if not math.isclose(avg, -neg_avg):
            continue  # 낡은 값 (그룹 크기가 바뀜). 최신 값은 따로 힙에 들어가 있다
        if avg < threshold:
            break  # 힙 최댓값이 기준 미만이면 더 합칠 쌍이 없다

        score, i, j, reason = best[k]
        links.append(
            GroupLink(a=commits[i].sha, b=commits[j].sha, score=round(avg, 3), reason=f"그룹 평균 {avg:.2f} | 대표 쌍 {reason}")
        )

        # b를 a에 흡수
        members[a].extend(members.pop(b))
        del total[k]
        best.pop(k, None)
        neighbors[a].discard(b)
        for x in neighbors.pop(b):
            if x == a:
                continue
            old, new = key(b, x), key(a, x)
            total[new] = total.get(new, 0.0) + total.pop(old)
            cand = best.pop(old)
            if new not in best or cand[0] > best[new][0]:
                best[new] = cand
            neighbors[x].discard(b)
            neighbors[x].add(a)
            neighbors[a].add(x)
        # a의 크기가 바뀌었으니 a와 이웃한 모든 쌍의 평균을 새로 넣는다
        for x in neighbors[a]:
            nk = key(a, x)
            heapq.heappush(heap, (-average(nk), nk))

    return list(members.values()), links


# ----------------------------------------------------------------------
# 특징 추출
# ----------------------------------------------------------------------


def path_features(c: Commit) -> set[str]:
    """바뀐 파일 경로 + 그 상위 폴더들. 예) lib/desk3d/scene.ts → {파일, lib/desk3d/, lib/}

    문서 파일(README 등)은 뺀다. 기능 작업 커밋이 README를 같이 고쳤다는 이유로
    다른 기능과 묶이지 않게 하기 위해서다.
    """
    files = [f for f in c.included_files if not is_doc_file(f.path)]
    feats: set[str] = set()
    for f in files:
        for path in filter(None, (f.path, f.old_path)):
            feats.add(path)
            feats.update(f"{parent}/" for parent in PurePosixPath(path).parents if str(parent) != ".")
    return feats


_TOKEN = re.compile(r"\d+[a-z]+|[a-z][a-z0-9+#]*|[가-힣]+")
# 커밋 끝의 서명 줄 (Co-Authored-By:, Signed-off-by: 등) → 작업 내용과 무관
_TRAILER = re.compile(r"^[A-Za-z-]+-by:.*$", re.MULTILINE | re.IGNORECASE)
# 어떤 작업에나 붙는 단어라 '같은 작업' 판단에 도움이 안 됨
_STOPWORDS = {
    "fix", "fixed", "update", "updated", "add", "added", "remove", "change", "refactor", "chore",
    "wip", "the", "an", "and", "to", "of", "for", "in", "on", "with", "feat", "docs", "style",
    "추가", "수정", "변경", "제거", "개선", "정리", "반영", "적용", "새로", "작성",
}  # fmt: skip


def message_tokens(message: str) -> set[str]:
    """커밋 메시지 → 비교용 토큰 집합.

    영어는 단어 단위, 한국어는 글자 2개씩 자른 bigram을 쓴다.
    한국어는 '화면을/화면으로/화면'처럼 조사·어미가 붙어 단어가 계속 바뀌는데,
    bigram이면 형태소 분석기 없이도 '화면'이라는 공통 조각이 겹친다.
    """
    text = _TRAILER.sub("", message).lower()
    tokens: set[str] = set()
    for tok in _TOKEN.findall(text):
        if tok in _STOPWORDS:
            continue
        if tok[0] >= "가":  # 한글
            if len(tok) == 1:
                tokens.add(tok)
            else:
                tokens.update(tok[i : i + 2] for i in range(len(tok) - 1))
        elif len(tok) >= 2:
            tokens.add(tok)
    return tokens


def _words(message: str) -> list[str]:
    """화면 표시용: 커밋 제목의 단어를 bigram으로 쪼개지 않고 그대로."""
    title = message.split("\n", 1)[0].lower()
    return [w for w in _TOKEN.findall(title) if len(w) >= 2 and w not in _STOPWORDS]


def _keywords(commits: list[Commit], msg_idf: dict[str, float], k: int) -> list[str]:
    """그룹 대표 단어: (그룹 안 등장 횟수) × (단어를 이루는 토큰의 평균 IDF)가 큰 순."""
    counts = Counter(w for c in commits for w in dict.fromkeys(_words(c.message)))

    def weight(word: str) -> float:
        toks = message_tokens(word)
        return sum(msg_idf.get(t, 0.0) for t in toks) / len(toks) if toks else 0.0

    return sorted(counts, key=lambda w: (-counts[w] * weight(w), w))[:k]


def idf(docs: list[set[str]]) -> dict[str, float]:
    """idf = log((N+1)/df). 모든 커밋에 나오는 특징은 0에 가깝고, 드물수록 커진다."""
    n = len(docs)
    df = Counter(t for d in docs for t in d)
    return {t: math.log((n + 1) / cnt) for t, cnt in df.items()}


def weighted_jaccard(a: set[str], b: set[str], weights: dict[str, float]) -> float:
    union = sum(weights[t] for t in a | b)
    if union == 0:
        return 0.0
    return sum(weights[t] for t in a & b) / union


def weighted_overlap(a: set[str], b: set[str], weights: dict[str, float]) -> float:
    """교집합 / 작은 쪽. 작은 커밋이 큰 커밋의 일부를 그대로 건드렸을 때 높게 나온다."""
    smaller = min(sum(weights[t] for t in a), sum(weights[t] for t in b))
    if smaller == 0:
        return 0.0
    return sum(weights[t] for t in a & b) / smaller


def similarity(a: set[str], b: set[str], weights: dict[str, float]) -> float:
    """Jaccard와 overlap의 평균.

    Jaccard만 쓰면 '버전 번호 1줄 수정' 커밋이 같은 폴더를 크게 바꾼 커밋과 거의 0점이 되고,
    overlap만 쓰면 모든 걸 건드린 거대 커밋이 다리가 되어 전부 한 그룹으로 이어진다.
    둘을 섞어 양쪽 문제를 줄인다.
    """
    return (weighted_jaccard(a, b, weights) + weighted_overlap(a, b, weights)) / 2


def _top_features(docs: Iterable[set[str]], weights: dict[str, float], k: int, dirs_only: bool = False) -> list[str]:
    counts = Counter(t for d in docs for t in d if not dirs_only or t.endswith("/") or "/" not in t)
    ranked = sorted(counts, key=lambda t: (-counts[t] * weights[t], t))
    return ranked[:k]
