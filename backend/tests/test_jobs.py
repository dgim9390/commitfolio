"""작업 저장소와 '직접 수정' API 테스트 (실제 분석은 돌리지 않는다)."""

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.api.jobs import AnalyzeRequest, Job, JobNotReadyError, JobStore
from app.models import Contribution, Outputs, Portfolio, Statement

REQ = AnalyzeRequest(repo_url="o/r", username="u")


def outputs(tagline: str) -> Outputs:
    s = Statement(text="직접 쓴 문장", evidence=[], edited=True)
    return Outputs(
        portfolio=Portfolio(tagline=tagline, overview="o", tech_stack=[],
                            contributions=[Contribution(title="t", summary=s, points=[], technologies=[])]),
        slides=[],
    )


def done_job(store: JobStore, job_id: str = "abc123") -> Job:
    job = Job(id=job_id, request=REQ, status="done")
    store._jobs[job.id] = job
    store._save(job)
    return job


def test_finished_jobs_survive_restart(tmp_path):
    done_job(JobStore(tmp_path))
    restarted = JobStore(tmp_path)  # 새 저장소 = 서버 재시작
    job = restarted.get("abc123")
    assert job is not None and job.status == "done"


def test_save_and_reset_edits(tmp_path):
    store = JobStore(tmp_path)
    done_job(store)
    store.save_edits("abc123", outputs("고친 소개"))

    reloaded = JobStore(tmp_path).get("abc123")
    assert reloaded.edited_outputs.portfolio.tagline == "고친 소개"
    assert reloaded.edited_outputs.portfolio.contributions[0].summary.edited
    assert reloaded.edited_at is not None

    store.save_edits("abc123", None)
    assert JobStore(tmp_path).get("abc123").edited_outputs is None


def test_edit_rules(tmp_path):
    store = JobStore(tmp_path)
    store._jobs["run1"] = Job(id="run1", request=REQ, status="running")
    with pytest.raises(JobNotReadyError):
        store.save_edits("run1", outputs("x"))
    assert store.save_edits("nope", outputs("x")) is None
    # 주소창에서 온 이상한 ID로 다른 경로의 파일을 읽지 못한다
    assert store.get("../../etc/passwd") is None


def test_edit_api(tmp_path, monkeypatch):
    store = JobStore(tmp_path)
    done_job(store)
    store._jobs["run1"] = Job(id="run1", request=REQ, status="running")
    monkeypatch.setattr(main, "jobs", store)
    client = TestClient(main.app)

    body = outputs("API로 고침").model_dump(mode="json")
    r = client.put("/api/jobs/abc123/outputs", json=body)
    assert r.status_code == 200 and r.json()["edited_outputs"]["portfolio"]["tagline"] == "API로 고침"

    assert client.delete("/api/jobs/abc123/outputs").json()["edited_outputs"] is None
    assert client.put("/api/jobs/run1/outputs", json=body).status_code == 409
    assert client.put("/api/jobs/missing/outputs", json=body).status_code == 404
