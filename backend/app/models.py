"""파이프라인 전 단계가 공유하는 데이터 타입.

수집 → 필터링 → 그룹화 → 요약 → 생성 단계는 모두 이 타입들을 주고받는다.
pydantic 모델이라 그대로 JSON 저장/API 응답으로 쓸 수 있다.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class FileChange(BaseModel):
    path: str
    old_path: str | None = None  # 이름이 바뀐 경우 이전 경로
    status: Literal["added", "modified", "deleted", "renamed"] = "modified"
    additions: int = 0
    deletions: int = 0
    is_binary: bool = False
    patch: str | None = None  # 필터링 후 LLM에 보낼 diff (잘렸을 수 있음)
    excluded_reason: str | None = None  # None이면 분석 대상, 아니면 제외 이유 코드
    truncated: bool = False

    @property
    def lines_changed(self) -> int:
        return self.additions + self.deletions


class Commit(BaseModel):
    sha: str
    url: str  # 근거 링크로 표시할 GitHub 커밋 페이지
    message: str
    authored_at: datetime
    author_login: str | None
    is_merge: bool = False
    diff_available: bool = True  # 로컬 클론에서 커밋을 못 찾은 경우 False
    files: list[FileChange] = Field(default_factory=list)
    pr_number: int | None = None

    @property
    def title(self) -> str:
        return self.message.split("\n", 1)[0]

    @property
    def short_sha(self) -> str:
        return self.sha[:7]

    @property
    def included_files(self) -> list[FileChange]:
        return [f for f in self.files if f.excluded_reason is None]


class PullRequest(BaseModel):
    number: int
    title: str
    body: str
    url: str
    merged_at: datetime
    commit_shas: list[str] = Field(default_factory=list)


class RepoInfo(BaseModel):
    owner: str
    name: str
    url: str
    description: str | None
    default_branch: str
    topics: list[str] = Field(default_factory=list)
    languages: dict[str, int] = Field(default_factory=dict)  # 레포 전체 기준 (바이트)
    readme: str | None = None


class ApiStats(BaseModel):
    requests: int = 0  # 실제로 GitHub에 보낸 요청 수
    not_modified: int = 0  # 그중 304 (캐시 재사용) 응답 수
    authenticated: bool = False
    rate_limit_limit: int | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset: datetime | None = None


class CollectStats(BaseModel):
    repo_commits_in_range: int  # 기간 내 기본 브랜치 전체 커밋 수 (작성자 무관)
    user_commits: int  # 그중 이 사용자의 커밋 수 (머지 커밋 포함)
    merge_commits: int
    files_total: int
    files_excluded: int
    excluded_by_reason: dict[str, int]
    files_truncated: int
    user_languages: dict[str, int]  # 이 사용자가 바꾼 줄 수 기준 언어 비율
    api: ApiStats


class GroupLink(BaseModel):
    """두 커밋을 같은 그룹으로 묶은 근거 (결과 설명·튜닝용)."""

    a: str  # 커밋 SHA
    b: str
    score: float
    reason: str


class WorkGroup(BaseModel):
    """'기능 단위 작업' 하나. 4단계에서 그룹마다 LLM 요약을 한 번 한다."""

    id: int
    commit_shas: list[str]  # 오래된 순
    started_at: datetime
    ended_at: datetime
    paths: list[str] = Field(default_factory=list)  # 이 작업을 대표하는 경로
    keywords: list[str] = Field(default_factory=list)  # 커밋 메시지에서 뽑은 대표 단어
    links: list[GroupLink] = Field(default_factory=list)


class ExcludedCommit(BaseModel):
    sha: str
    reason: str  # rules.EXCLUDE_LABELS의 키


class GroupingResult(BaseModel):
    groups: list[WorkGroup]  # 시작 시각 순
    excluded: list[ExcludedCommit] = Field(default_factory=list)  # 분석에서 뺀 커밋


class CollectResult(BaseModel):
    repo: RepoInfo
    username: str
    since: date | None
    until: date | None
    commits: list[Commit]  # 오래된 순
    pull_requests: list[PullRequest]
    stats: CollectStats
    collected_at: datetime


# ----------------------------------------------------------------------
# 4단계: 요약·생성 결과
# ----------------------------------------------------------------------


class Fact(BaseModel):
    """수치나 구체적 사실. 원문 인용(quote)이 있어야 문장에 쓸 수 있다."""

    statement: str
    evidence: str  # 커밋 SHA
    quote: str  # 커밋 메시지나 diff에서 그대로 옮긴 부분


class GroupSummary(BaseModel):
    group_id: int
    title: str
    problem: str  # 어떤 문제/필요가 있었는지
    solution: str  # 어떻게 해결했는지
    technologies: list[str]
    significance: Literal["major", "minor"]
    evidence: list[str]  # 커밋 SHA
    key_points: list[str] = Field(default_factory=list)  # 구체적인 구현 포인트
    decisions: list[str] = Field(default_factory=list)  # 코드에서 확인되는 설계 판단과 이유
    facts: list[Fact] = Field(default_factory=list)


class Statement(BaseModel):
    """결과 문장 하나 + 근거."""

    text: str
    evidence: list[str]  # 커밋 SHA (화면에서 커밋 링크로 표시)
    from_readme: bool = False  # README·레포 설명이 근거인 문장 (프로젝트 소개 등)
    warnings: list[str] = Field(default_factory=list)  # 검증에서 발견한 문제 (예: 근거 없는 수치)
    edited: bool = False  # 사용자가 직접 고치거나 추가한 문장 (AI가 근거로 확인한 문장과 구분)


class Contribution(BaseModel):
    """포트폴리오의 주요 기여 하나: 제목 → 한 줄 요약 → 구체 포인트 → 기술 태그."""

    title: str
    summary: Statement
    points: list[Statement]
    technologies: list[str]


class TechGroup(BaseModel):
    category: str  # 예: "Frontend", "3D·그래픽"
    items: list[str]


class Portfolio(BaseModel):
    tagline: str  # 한 줄 소개
    overview: str
    contributions: list[Contribution]
    tech_stack: list[TechGroup]


class SlidePoint(Statement):
    heading: str  # 굵게 보이는 짧은 키워드


class Highlight(BaseModel):
    """슬라이드의 큰 숫자 카드. 근거에서 확인된 수치만 남긴다."""

    value: str  # 예: "19종", "50단계"
    label: str
    evidence: list[str]
    from_readme: bool = False


SlideLayout = Literal["cover", "agenda", "problem", "feature", "architecture", "tech", "summary"]


class Slide(BaseModel):
    layout: SlideLayout
    title: str
    headline: str  # 이 장의 핵심 메시지 한 문장
    points: list[SlidePoint]
    highlights: list[Highlight] = Field(default_factory=list)
    flow: list[str] = Field(default_factory=list)  # architecture: 처리 흐름 단계
    notes: str  # 발표자 메모


class Outputs(BaseModel):
    portfolio: Portfolio
    slides: list[Slide]


class LLMUsage(BaseModel):
    model: str
    calls: int = 0  # 실제 API 호출 수
    cached_calls: int = 0  # 로컬 캐시로 대신한 호출 수
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float | None = None  # 모델 단가를 알 때만


class CommitRef(BaseModel):
    """화면 표시용 커밋 요약 (diff 제외)."""

    sha: str
    url: str
    title: str
    authored_at: datetime


class AnalysisResult(BaseModel):
    repo: RepoInfo
    username: str
    since: date | None
    until: date | None
    commits: list[CommitRef]
    grouping: GroupingResult
    summaries: list[GroupSummary]
    outputs: Outputs
    validation_notes: list[str]  # 검증에서 빼거나 고친 내용
    usage: LLMUsage
