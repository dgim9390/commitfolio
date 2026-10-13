"""분석 작업 관리.

분석은 수십 초~수 분 걸리므로 요청을 받으면 바로 job_id를 돌려주고 백그라운드 스레드에서
돌린다. 프론트는 GET /api/jobs/{id}를 주기적으로 물어봐서(폴링) 진행 상황을 그린다.
끝난 작업(결과 + 사용자가 직접 고친 내용)은 .cache/jobs/{id}.json 에도 저장해서,
서버를 재시작해도 같은 링크(?job=...)로 다시 열 수 있다. 진행 중인 작업은 메모리에만 있다.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.errors import CommitFolioError
from app.models import AnalysisResult, Outputs
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
    # 사용자가 직접 고친 결과. 없으면 result.outputs(AI 원본)를 그대로 쓴다
    edited_outputs: Outputs | None = None
    edited_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobNotReadyError(Exception):
    """아직 끝나지 않았거나 실패한 작업의 결과를 고치려 할 때."""


class JobStore:
    def __init__(self, save_dir: Path, max_workers: int = 2):
        self._jobs: dict[str, Job] = {}
        self._dir = save_dir
        self._dir.mkdir(parents=True, exist_ok=True)
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
        if job_id in self._jobs:
            return self._jobs[job_id]
        # 메모리에 없으면(서버 재시작 등) 저장된 파일에서 불러온다
        path = self._path(job_id)
        if path is None or not path.exists():
            return None
        job = Job.model_validate_json(path.read_text(encoding="utf-8"))
        with self._lock:
            return self._jobs.setdefault(job.id, job)

    def save_edits(self, job_id: str, outputs: Outputs | None) -> Job | None:
        """사용자가 고친 결과를 저장한다. outputs=None이면 AI 원본으로 되돌린다."""
        job = self.get(job_id)
        if job is None:
            return None
        if job.status != "done":
            raise JobNotReadyError()
        job.edited_outputs = outputs
        job.edited_at = datetime.now(timezone.utc) if outputs else None
        self._save(job)
        return job

    def _path(self, job_id: str) -> Path | None:
        # 주소창에서 온 값이므로 파일 경로로 쓰기 전에 형식을 확인한다 (../ 같은 경로 조작 방지)
        if not job_id.isalnum() or len(job_id) > 32:
            return None
        return self._dir / f"{job_id}.json"

    def _save(self, job: Job) -> None:
        path = self._path(job.id)
        if path:
            path.write_text(job.model_dump_json(), encoding="utf-8")

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
            self._save(job)
        except CommitFolioError as e:  # 사용자에게 보여줄 수 있는 에러
            job.status, job.error = "error", str(e)
        except Exception as e:  # 예상 못 한 버그: 내용은 서버 로그에, 화면엔 짧게
            import traceback

            traceback.print_exc()
            job.status, job.error = "error", f"예상하지 못한 오류가 발생했습니다 ({type(e).__name__}). 서버 로그를 확인하세요."
