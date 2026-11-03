"""실험 평가 지표. 외부 라이브러리 없이 정의대로 계산한다 (각 함수는 tests/test_experiments.py에서 검증).

- ari: Adjusted Rand Index. 두 그룹 나누기가 얼마나 같은지 (1=완전히 같음, 0=무작위 수준)
- nmi: Normalized Mutual Information. 0~1, 클수록 비슷
- cohen_kappa: 두 판정자(AI·사람)의 일치도에서 우연히 맞을 확률을 뺀 값
"""

import math
from collections import Counter


def _comb2(n: int) -> int:
    return n * (n - 1) // 2


def ari(labels_a: list, labels_b: list) -> float:
    n = len(labels_a)
    pairs = Counter(zip(labels_a, labels_b))
    index = sum(_comb2(v) for v in pairs.values())
    sum_a = sum(_comb2(v) for v in Counter(labels_a).values())
    sum_b = sum(_comb2(v) for v in Counter(labels_b).values())
    expected = sum_a * sum_b / _comb2(n) if n > 1 else 0.0
    maximum = (sum_a + sum_b) / 2
    if maximum == expected:  # 둘 다 전부 한 그룹이거나 전부 따로인 경우
        return 1.0
    return (index - expected) / (maximum - expected)


def _entropy(labels: list) -> float:
    n = len(labels)
    return -sum(c / n * math.log(c / n) for c in Counter(labels).values())


def nmi(labels_a: list, labels_b: list) -> float:
    n = len(labels_a)
    ha, hb = _entropy(labels_a), _entropy(labels_b)
    if ha == 0 and hb == 0:
        return 1.0
    count_a, count_b = Counter(labels_a), Counter(labels_b)
    mutual = sum(
        c / n * math.log(c * n / (count_a[a] * count_b[b])) for (a, b), c in Counter(zip(labels_a, labels_b)).items()
    )
    return mutual / ((ha + hb) / 2)


def cohen_kappa(labels_a: list, labels_b: list) -> float:
    n = len(labels_a)
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    count_a, count_b = Counter(labels_a), Counter(labels_b)
    chance = sum(count_a[k] * count_b[k] for k in count_a) / (n * n)
    if chance == 1:
        return 1.0
    return (observed - chance) / (1 - chance)
