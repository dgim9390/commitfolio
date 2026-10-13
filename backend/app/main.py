"""FastAPI 앱. 개발 중에는 Vite 개발 서버가 /api 요청을 이쪽(8000번 포트)으로 넘겨준다.

실행: uv run uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException

from app.api.jobs import STAGES, AnalyzeRequest, Job, JobNotReadyError, JobStore
from app.config import get_settings
from app.models import Outputs

app = FastAPI(title="CommitFolio API")
jobs = JobStore(get_settings().cache_dir / "jobs")

_NOT_FOUND = "작업을 찾을 수 없습니다. 링크가 맞는지 확인하거나 다시 분석을 시작하세요."


@app.post("/api/analyze")
def start_analysis(req: AnalyzeRequest) -> dict:
    job = jobs.submit(req)
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> Job:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, _NOT_FOUND)
    return job


@app.put("/api/jobs/{job_id}/outputs")
def save_edited_outputs(job_id: str, outputs: Outputs) -> Job:
    """사용자가 직접 고친 포트폴리오·발표 자료를 저장한다."""
    return _save_edits(job_id, outputs)


@app.delete("/api/jobs/{job_id}/outputs")
def reset_edited_outputs(job_id: str) -> Job:
    """직접 고친 내용을 버리고 AI 원본으로 되돌린다."""
    return _save_edits(job_id, None)


def _save_edits(job_id: str, outputs: Outputs | None) -> Job:
    try:
        job = jobs.save_edits(job_id, outputs)
    except JobNotReadyError:
        raise HTTPException(409, "분석이 끝난 결과만 수정할 수 있습니다.") from None
    if job is None:
        raise HTTPException(404, _NOT_FOUND)
    return job


@app.get("/api/stages")
def get_stages() -> list[str]:
    return STAGES
