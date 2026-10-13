"""분석 작업 관리.

분석은 수십 초~수 분 걸리므로 요청을 받으면 바로 job_id를 돌려주고 백그라운드 스레드에서
돌린다. 프론트는 GET /api/jobs/{id}를 주기적으로 물어봐서(폴링) 진행 상황을 그린다.
MVP라서 작업 상태는 메모리에만 둔다 (서버를 재시작하면 목록은 사라지지만 GitHub·LLM 캐시는 남음).
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from app.errors import CommitFolioError
from app.models import AnalysisResult
from app.pipeline.runner import analyze

# 진행 단계 (프론트 체크리스트 순서). 수집 단계의 세부 이름들은 앞쪽 단계로 합친다.
STAGES = ["collect", "group", "summarize", "generate", "validate"]
_STAGE_OF = {
    "repo": "collect", "commits": "collect", "pulls": "collect", "clone": "collect",
    "diffs": "collect", "filter": "collect",
}  # fmt: skip


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(min_length=1)
    username: str = Field(min_length=1)
    since: date | None = None
    until: date | None = None


class Job(BaseModel):
    id: str
    request: AnalyzeRequest
    status: Literal["queued", "running", "done", "error"] = "queued"
    stage: str | None = None  # STAGES 중 하나
    message: str = "대기 중"
    error: str | None = None
    result: AnalysisResult | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobStore:
    def __init__(self, max_workers: int = 2):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        # 동시에 너무 많이 돌면 GitHub·Gemini 한도를 금방 쓰므로 작업 수를 제한한다
        self._pool = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, req: AnalyzeRequest) -> Job:
        with self._lock:
            # 같은 요청이 이미 진행 중이면 새로 만들지 않고 그 작업을 돌려준다 (중복 클릭 방지)
            for job in self._jobs.values():
                if job.request == req and job.status in ("queued", "running"):
                    return job
            job = Job(id=uuid.uuid4().hex[:12], request=req)
            self._jobs[job.id] = job
        self._pool.submit(self._run, job)
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def _run(self, job: Job) -> None:
        def progress(stage: str, message: str) -> None:
            job.stage = _STAGE_OF.get(stage, stage)
            job.message = message

        job.status = "running"
        try:
            req = job.request
            job.result = analyze(req.repo_url.strip(), req.username.strip(), req.since, req.until, progress=progress)
            job.status = "done"
            job.message = "완료"
        except CommitFolioError as e:  # 사용자에게 보여줄 수 있는 에러
            job.status, job.error = "error", str(e)
        except Exception as e:  # 예상 못 한 버그: 내용은 서버 로그에, 화면엔 짧게
            import traceback

            traceback.print_exc()
            job.status, job.error = "error", f"예상하지 못한 오류가 발생했습니다 ({type(e).__name__}). 서버 로그를 확인하세요."
