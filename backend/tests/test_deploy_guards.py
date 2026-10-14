"""배포용 보호 장치: 접근 코드, 하루 분석 횟수 제한, 큰 레포 거절."""

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.api.jobs import Job, JobStore
from app.api.limits import DailyLimiter, LimitExceeded
from app.errors import RepoTooLargeError, TooManyCommitsError
from app.github.collector import _fetch_repo_info

BODY = {"repo_url": "o/r", "username": "u"}


class FakeStore(JobStore):
    """실제 분석은 돌리지 않고 작업만 만든다."""

    def submit(self, req):
        job = Job(id=f"job{len(self._jobs)}", request=req, status="done")
        self._jobs[job.id] = job
        return job


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "jobs", FakeStore(tmp_path))
    monkeypatch.setattr(main.settings, "access_code", "")
    monkeypatch.setattr(main, "limiter", DailyLimiter(0, 0))
    return TestClient(main.app)


def test_access_code(client, monkeypatch):
    assert client.get("/api/config").json() == {"access_code_required": False}
    assert client.post("/api/analyze", json=BODY).status_code == 200

    monkeypatch.setattr(main.settings, "access_code", "secret-123")
    assert client.get("/api/config").json() == {"access_code_required": True}
    assert client.post("/api/analyze", json=BODY).status_code == 401
    assert client.post("/api/analyze", json=BODY, headers={"X-Access-Code": "wrong"}).status_code == 401
    assert client.get("/api/jobs/job0").status_code == 401  # 결과 보기도 막힘
    assert client.get("/api/access", headers={"X-Access-Code": "wrong"}).status_code == 401
    assert client.get("/api/access", headers={"X-Access-Code": "secret-123"}).status_code == 200
    ok = client.post("/api/analyze", json={**BODY, "username": "v"}, headers={"X-Access-Code": "secret-123"})
    assert ok.status_code == 200


def test_daily_limit_per_ip(client, monkeypatch):
    monkeypatch.setattr(main, "limiter", DailyLimiter(total=0, per_ip=2))
    for name in ("a", "b"):
        assert client.post("/api/analyze", json={**BODY, "username": name}).status_code == 200
    r = client.post("/api/analyze", json={**BODY, "username": "c"})
    assert r.status_code == 429 and "분석 가능 횟수" in r.json()["detail"]
    # 다른 IP는 아직 가능 (호스팅 프록시가 X-Forwarded-For 끝에 붙이는 값 기준)
    other = client.post("/api/analyze", json={**BODY, "username": "d"}, headers={"X-Forwarded-For": "1.2.3.4"})
    assert other.status_code == 200
    # 방문자가 앞에 가짜 IP를 넣어도 마지막 값(프록시가 붙인 실제 IP)으로 센다
    spoof = client.post("/api/analyze", json={**BODY, "username": "e"}, headers={"X-Forwarded-For": "9.9.9.9, 1.2.3.4"})
    assert spoof.status_code == 200
    blocked = client.post("/api/analyze", json={**BODY, "username": "f"}, headers={"X-Forwarded-For": "8.8.8.8, 1.2.3.4"})
    assert blocked.status_code == 429


def test_total_limit():
    limiter = DailyLimiter(total=1, per_ip=0)
    limiter.check("a")
    limiter.count("a")
    with pytest.raises(LimitExceeded, match="전체"):
        limiter.check("b")


class FakeClient:
    def __init__(self, size_kb: int):
        self.size_kb = size_kb

    def get(self, path, params=None):
        return {"owner": {"login": "o"}, "name": "r", "size": self.size_kb, "html_url": "", "default_branch": "main"}


def test_repo_too_large():
    with pytest.raises(RepoTooLargeError, match="너무 큽니다"):
        _fetch_repo_info(FakeClient(size_kb=900 * 1024), "o", "r", max_size_mb=500)


def test_too_many_commits_message():
    assert "기간을 좁혀" in str(TooManyCommitsError(800, 400))


def test_client_ip_with_two_proxies(monkeypatch):
    """Vercel → Render처럼 프록시가 두 겹이면 뒤에서 두 번째가 실제 방문자."""
    from starlette.requests import Request

    def req(xff: str) -> Request:
        return Request({"type": "http", "headers": [(b"x-forwarded-for", xff.encode())], "client": ("10.0.0.1", 1)})

    monkeypatch.setattr(main.settings, "proxy_hops", 2)
    assert main.client_ip(req("6.6.6.6, 1.2.3.4, 76.76.21.21")) == "1.2.3.4"  # 위장 값·Vercel IP 무시
    assert main.client_ip(req("1.2.3.4")) == "1.2.3.4"  # 값이 하나뿐이면 그 값
    monkeypatch.setattr(main.settings, "proxy_hops", 1)
    assert main.client_ip(req("6.6.6.6, 1.2.3.4")) == "1.2.3.4"
