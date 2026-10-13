"""FastAPI 앱.

- 개발: Vite 개발 서버(5173)가 /api 요청을 이쪽(8000)으로 넘겨준다
  uv run uvicorn app.main:app --reload --port 8000
- 배포: 빌드된 프론트엔드(frontend/dist)가 있으면 이 서버가 화면까지 함께 내보낸다 → 주소 하나로 동작
"""

import secrets

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from app.api.jobs import STAGES, AnalyzeRequest, Job, JobNotReadyError, JobStore
from app.api.limits import DailyLimiter, LimitExceeded
from app.config import get_settings
from app.models import Outputs

settings = get_settings()
app = FastAPI(title="CommitFolio API")
jobs = JobStore(settings.cache_dir / "jobs")
limiter = DailyLimiter(settings.daily_analysis_limit, settings.per_ip_daily_limit)

_NOT_FOUND = "작업을 찾을 수 없습니다. 링크가 맞는지 확인하거나 다시 분석을 시작하세요."


def require_access(x_access_code: str | None = Header(default=None)) -> None:
    """ACCESS_CODE가 설정돼 있으면, 요청 헤더의 코드가 맞아야 통과."""
    expected = settings.access_code
    # compare_digest: 글자를 하나씩 맞혀 보는 시간 차 공격을 막는 비교
    if expected and not secrets.compare_digest((x_access_code or "").encode(), expected.encode()):
        raise HTTPException(401, "접근 코드가 필요합니다.")


def client_ip(request: Request) -> str:
    # 배포 서버는 앞단 프록시를 거치므로 접속 IP는 X-Forwarded-For에 있다.
    # 첫 값은 방문자가 마음대로 넣을 수 있어서(IP 제한 우회), 호스팅 프록시가 붙인 마지막 값을 쓴다
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


@app.get("/api/config")
def get_config() -> dict:
    """화면이 처음 열릴 때 접근 코드 입력 칸을 보여줄지 정하는 데 쓴다 (코드 없이 호출 가능)."""
    return {"access_code_required": bool(settings.access_code)}


@app.get("/api/access", dependencies=[Depends(require_access)])
def check_access() -> dict:
    """접근 코드 입력 화면에서 코드가 맞는지 바로 확인할 때 쓴다."""
    return {"ok": True}


@app.post("/api/analyze", dependencies=[Depends(require_access)])
def start_analysis(req: AnalyzeRequest, request: Request) -> dict:
    if existing := jobs.find_running(req):  # 이미 진행 중인 같은 요청은 횟수를 세지 않는다
        return {"job_id": existing.id}
    ip = client_ip(request)
    try:
        limiter.check(ip)
    except LimitExceeded as e:
        raise HTTPException(429, str(e)) from None
    job = jobs.submit(req)
    limiter.count(ip)
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}", dependencies=[Depends(require_access)])
def get_job(job_id: str) -> Job:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, _NOT_FOUND)
    return job


@app.put("/api/jobs/{job_id}/outputs", dependencies=[Depends(require_access)])
def save_edited_outputs(job_id: str, outputs: Outputs) -> Job:
    """사용자가 직접 고친 포트폴리오·발표 자료를 저장한다."""
    return _save_edits(job_id, outputs)


@app.delete("/api/jobs/{job_id}/outputs", dependencies=[Depends(require_access)])
def reset_edited_outputs(job_id: str) -> Job:
    """직접 고친 내용을 버리고 AI 원본으로 되돌린다."""
    return _save_edits(job_id, None)


@app.get("/api/stages")
def get_stages() -> list[str]:
    return STAGES


def _save_edits(job_id: str, outputs: Outputs | None) -> Job:
    try:
        job = jobs.save_edits(job_id, outputs)
    except JobNotReadyError:
        raise HTTPException(409, "분석이 끝난 결과만 수정할 수 있습니다.") from None
    if job is None:
        raise HTTPException(404, _NOT_FOUND)
    return job


# 화면(빌드된 프론트엔드). API 경로를 모두 등록한 뒤에 붙여야 /api 요청을 가로채지 않는다
if settings.static_dir.is_dir():
    app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="web")
