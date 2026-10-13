"""FastAPI 앱. 개발 중에는 Vite 개발 서버가 /api 요청을 이쪽(8000번 포트)으로 넘겨준다.

실행: uv run uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException

from app.api.jobs import STAGES, AnalyzeRequest, Job, JobStore

app = FastAPI(title="CommitFolio API")
jobs = JobStore()


@app.post("/api/analyze")
def start_analysis(req: AnalyzeRequest) -> dict:
    job = jobs.submit(req)
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> Job:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "작업을 찾을 수 없습니다. 서버가 재시작됐다면 다시 분석을 시작하세요.")
    return job


@app.get("/api/stages")
def get_stages() -> list[str]:
    return STAGES
