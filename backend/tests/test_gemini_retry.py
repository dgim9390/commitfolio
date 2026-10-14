"""Gemini 혼잡(503)·한도(429) 대응: 실제 API 대신 정해진 오류를 내는 가짜 클라이언트로 확인."""

from types import SimpleNamespace

import pytest
from google.genai import errors
from pydantic import BaseModel

import app.pipeline.llm as llm_module
from app.config import Settings
from app.errors import LLMError
from app.pipeline.llm import GeminiLLM


class Answer(BaseModel):
    ok: bool


def api_error(code: int, message: str = "busy") -> errors.APIError:
    return errors.APIError(code, {"error": {"code": code, "message": message, "status": "UNAVAILABLE"}})


class FakeModels:
    """모델별로 미리 정한 결과(오류 또는 성공)를 순서대로 돌려준다."""

    def __init__(self, plan: dict[str, list]):
        self.plan = plan
        self.calls: list[str] = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        outcome = self.plan[model].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text='{"ok": true}', usage_metadata=None)


def make_llm(plan, fallback="lite-model") -> tuple[GeminiLLM, FakeModels]:
    llm = GeminiLLM(Settings(gemini_api_key="test", llm_model="main-model", llm_fallback_model=fallback), cache=None)
    fake = FakeModels(plan)
    llm._client = SimpleNamespace(models=fake)
    return llm, fake


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(llm_module.time, "sleep", lambda s: None)


def test_busy_then_success_same_model():
    llm, fake = make_llm({"main-model": [api_error(503), api_error(503), "ok"]})
    assert llm.parse(system="s", prompt="p", schema=Answer).ok
    assert fake.calls == ["main-model"] * 3


def test_switches_to_fallback_when_main_stays_busy():
    llm, fake = make_llm({"main-model": [api_error(503)] * 4, "lite-model": ["ok"]})
    assert llm.parse(system="s", prompt="p", schema=Answer).ok
    assert fake.calls == ["main-model"] * 4 + ["lite-model"]
    assert "lite-model" in llm.usage.model  # 결과 화면에 대체 모델을 썼다고 표시


def test_all_busy_gives_friendly_error():
    llm, _ = make_llm({"main-model": [api_error(503)] * 4, "lite-model": [api_error(503)] * 4})
    with pytest.raises(LLMError, match="혼잡"):
        llm.parse(system="s", prompt="p", schema=Answer)


def test_daily_quota_fails_immediately():
    llm, fake = make_llm({"main-model": [api_error(429, "GenerateRequestsPerDayPerProjectPerModel exceeded")]})
    with pytest.raises(LLMError, match="하루 사용량"):
        llm.parse(system="s", prompt="p", schema=Answer)
    assert fake.calls == ["main-model"]  # 하루 한도는 기다려도 소용없으니 바로 실패


def test_per_minute_quota_retries():
    llm, fake = make_llm({"main-model": [api_error(429, "Please retry in 2s"), "ok"]})
    assert llm.parse(system="s", prompt="p", schema=Answer).ok
    assert fake.calls == ["main-model", "main-model"]
