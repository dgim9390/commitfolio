"""그룹화 알고리즘의 공통 인터페이스.

파이프라인은 Grouper.group()만 호출한다. 그래서 heuristic.py를 임베딩·클러스터링 같은
다른 방식으로 바꿔도 수집·요약 단계 코드는 건드릴 필요가 없다.
"""

from typing import Protocol

from app.models import Commit, GroupingResult


class Grouper(Protocol):
    def group(self, commits: list[Commit]) -> GroupingResult:
        """커밋 목록을 받아 기능 단위 작업 그룹들과 분석에서 뺀 커밋 목록을 돌려준다.

        머지 커밋을 제외한 모든 입력 커밋은 정확히 한 그룹 또는 excluded 중 한 곳에 들어가야 한다.
        """
        ...


class UnionFind:
    """서로소 집합. 'A와 B는 같은 작업'이라는 관계를 모아 연결 요소(=그룹)를 만든다."""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]  # 경로 압축 (path halving)
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> bool:
        """합쳤으면 True, 이미 같은 집합이었으면 False."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True

    def components(self) -> list[list[int]]:
        groups: dict[int, list[int]] = {}
        for i in range(len(self.parent)):
            groups.setdefault(self.find(i), []).append(i)
        return list(groups.values())
