"""근거 내용 일치도: 문장이 근거로 단 커밋과 실제로 관련 있는지 점수로 본다.

AI는 실제로 있는 커밋 ID를 달아도, 같은 작업의 엉뚱한 커밋을 고를 때가 있다
(예: "3D에서 드래그로 제품 이동" 문장에 '꺼진 화면 반사광' 커밋). 그래서 문장과 커밋에서
단어를 뽑아 얼마나 겹치는지 계산한다.

점수 계산
- 커밋 쪽 단어: 메시지 + 파일 경로 + diff. 코드 식별자는 쪼갠다 (useDeskStore → use, desk, store)
  README 같은 문서 파일은 뺀다: 프로젝트 전체 설명이라 어떤 문장과도 겹쳐 버린다
- 한국어는 두 글자 조각(bigram)으로 비교한다 (조사·어미가 달라도 겹치게)
- IDF 가중치: 여러 커밋에 흔한 단어는 거의 0점, 그 커밋에만 있는 단어가 중요하다
- 길이 보정(BM25 방식): 파일을 많이 바꾼 거대 커밋은 단어가 많아 무엇과도 잘 겹치므로 점수를 깎는다
- 어느 커밋에도 없는 문장 단어(AI가 바꿔 말한 표현)는 계산에서 뺀다

판정 (check_evidence) - 틀린 근거를 고치는 것만큼 맞는 근거를 지우지 않는 것이 중요해서 보수적으로 판단한다
- 근거 커밋이 1~2개인 문장에서, 다른 근거보다 훨씬 안 맞고 점수 자체도 낮은 커밋은 근거에서 뺀다
  (두 사실을 합친 문장은 근거마다 점수 차이가 커서, 상대 비교만으로 빼면 맞는 근거도 빠진다)
- 근거가 모두 약하고 같은 작업 그룹 안에 확실히 더 맞는 커밋이 있으면,
  근거가 1개였으면 그 커밋으로 바꾸고, 여러 개였으면 기존 근거는 두고 앞에 추가한다
- 근거가 모두 약한데 더 나은 후보도 없으면 경고만 붙인다
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from app.models import Commit
from app.pipeline.grouping.rules import is_doc_file

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*|[가-힣]+")
_CAMEL = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])")
# 어떤 문장·커밋에나 나와서 관련성 판단에 도움이 안 되는 말
_STOP = {
    "the", "and", "for", "with", "from", "this", "that", "const", "let", "return", "import", "export",
    "function", "true", "false", "null", "undefined", "new", "type", "string", "number",
    "구현", "추가", "적용", "개선", "처리", "기능", "통해", "위해", "했습니다", "합니다", "있도록", "있는",
}  # fmt: skip

# BM25 길이 보정 상수 (검색엔진에서 흔히 쓰는 값)
_K1, _B = 1.2, 0.75

# 판정 기준 (DeskBoard 결과로 조정)
WEAK_RATIO = 0.25  # 같은 문장의 가장 잘 맞는 근거보다 이 비율 미만이고
WEAK_ABS = 0.12  # 점수 자체도 이보다 낮으면 '안 맞는 근거'
SWITCH_RATIO = 2.0  # 후보 커밋이 현재 근거보다 이 배수 이상 잘 맞아야 근거를 바꾼다
SWITCH_MIN = 0.35  # 바꿀 후보의 최소 점수 (애매한 후보로는 바꾸지 않는다)
WARN_BELOW = 0.12  # 근거 점수가 이보다 낮은데 더 나은 후보가 없으면 경고


def tokens(text: str) -> set[str]:
    out: set[str] = set()
    for word in _WORD.findall(text):
        if word[0] >= "가":  # 한글 → bigram
            if word not in _STOP and len(word) >= 2:
                out.update(word[i : i + 2] for i in range(len(word) - 1))
            continue
        low = word.lower()
        if len(low) >= 3 and low not in _STOP:
            out.add(low)
        for part in _CAMEL.findall(word):
            p = part.lower()
            if len(p) >= 3 and p not in _STOP:
                out.add(p)
    return out


def _commit_text(c: Commit) -> str:
    files = [f for f in c.files if not is_doc_file(f.path)]
    return "\n".join([c.message] + [f.path for f in files] + [f.patch or "" for f in files])


@dataclass
class EvidenceCheck:
    evidence: list[str]  # 고친 근거 커밋 목록
    warning: str | None = None
    notes: list[str] = field(default_factory=list)


class RelevanceIndex:
    def __init__(self, commits: list[Commit], groups: list[list[str]] | None = None):
        self._tokens = {c.sha: tokens(_commit_text(c)) for c in commits}
        n = len(commits) or 1
        df = Counter(t for ts in self._tokens.values() for t in ts)
        self._idf = {t: math.log((n + 1) / k) for t, k in df.items()}
        avg = sum(len(ts) for ts in self._tokens.values()) / n or 1
        # 커밋별 길이 보정 배수: 평균 크기면 1, 거대 커밋일수록 작아진다
        self._norm = {
            sha: (_K1 + 1) / (1 + _K1 * (1 - _B + _B * len(ts) / avg)) for sha, ts in self._tokens.items()
        }
        self._group_of = {sha: i for i, g in enumerate(groups or []) for sha in g}
        self._groups = groups or []

    def score(self, text: str, sha: str) -> float:
        ts = [t for t in tokens(text) if t in self._idf]
        total = sum(self._idf[t] for t in ts)
        if total == 0 or sha not in self._tokens:
            return 0.0
        hit = sum(self._idf[t] for t in ts if t in self._tokens[sha])
        return hit / total * self._norm[sha]

    def candidates(self, shas: list[str]) -> set[str]:
        """근거 커밋들이 속한 작업 그룹의 모든 커밋 (근거를 바꿀 때의 후보)."""
        out = set(shas)
        for sha in shas:
            if sha in self._group_of:
                out.update(self._groups[self._group_of[sha]])
        return out

    def check_evidence(self, text: str, shas: list[str], short: dict[str, str] | None = None) -> EvidenceCheck:
        if not shas:
            return EvidenceCheck(evidence=[])
        label = short or {}
        name = lambda s: label.get(s, s[:7])  # noqa: E731
        scores = {s: self.score(text, s) for s in shas}
        top = max(scores.values())
        result = EvidenceCheck(evidence=list(shas))

        # 1) 근거가 1~2개인 구체적인 문장: 유독 안 맞는 근거는 뺀다 (3개 이상은 작업 전체를 묶는 요약 문장이라 두지 않음)
        if len(shas) <= 2 and top > 0:
            weak = [s for s in shas if scores[s] < top * WEAK_RATIO and scores[s] < WEAK_ABS]
            if weak and len(weak) < len(shas):
                result.evidence = [s for s in shas if s not in weak]
                result.notes.append(f"내용과 맞지 않는 근거 {', '.join(map(name, weak))}를 뺐습니다")
                top = max(scores[s] for s in result.evidence)

        # 2) 근거가 모두 약하면 같은 작업 그룹에서 더 맞는 커밋을 찾는다
        others = self.candidates(shas) - set(result.evidence)
        if others:
            best_score, best = max((self.score(text, s), s) for s in others)
            if best_score >= SWITCH_MIN and best_score >= top * SWITCH_RATIO:
                old = ", ".join(map(name, result.evidence))
                if len(result.evidence) == 1:
                    result.evidence = [best]
                    result.notes.append(f"근거를 {old}에서 더 맞는 {name(best)}로 바꿨습니다")
                else:  # 근거가 여럿이면 일부는 맞을 수 있으니 지우지 않고 더 맞는 커밋을 앞에 더한다
                    result.evidence = [best] + result.evidence
                    result.notes.append(f"더 맞는 근거 {name(best)}를 추가했습니다")
                return result

        if top < WARN_BELOW:
            result.warning = "근거 커밋과 내용이 잘 맞지 않을 수 있습니다"
        return result
