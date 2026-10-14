"""LLM 호출 래퍼. 제공자(Gemini / Claude)를 .env의 LLM_PROVIDER로 고른다.

공통 기능 (BaseLLM)
- 구조화 출력: pydantic 모델을 넘기면 그 JSON 스키마대로 응답을 받아 검증해서 돌려준다
- 로컬 캐시: 같은 제공자·모델·프롬프트·스키마면 저장된 응답 재사용 → 재분석 시 호출 0회
- 사용량 집계, 사용자용 한국어 에러(LLMError)

나머지 파이프라인은 parse()만 호출하므로 제공자를 바꿔도 수집·그룹화·프롬프트·검증은 그대로다.
"""

import hashlib
import json
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.config import Settings
from app.errors import LLMError
from app.models import LLMUsage

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODELS = {
    "gemini": "gemini-3.8-flash",  # 무료 등급에서 쓸 수 있는 가장 똑똑한 Flash (2026-10 기준)
    "claude": "claude-opus-5-5",
}


class LLMCache:
    """요청 해시 → 파싱된 응답(JSON). 여러 스레드에서 같이 쓰므로 잠금을 건다."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS llm_cache (key TEXT PRIMARY KEY, body TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            self._conn.commit()

    def get(self, key: str) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT body FROM llm_cache WHERE key = ?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, body: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO llm_cache VALUES (?, ?, ?)",
                (key, json.dumps(body, ensure_ascii=False), datetime.now(timezone.utc).isoformat()),
            )
            self._conn.commit()

    def close(self) -> None:
        self._conn.close()


class BaseLLM:
    provider = ""

    def __init__(self, settings: Settings, cache: LLMCache | None):
        self.model = settings.llm_model or DEFAULT_MODELS[self.provider]
        self.usage = LLMUsage(model=f"{self.provider}/{self.model}")
        self._cache = cache
        self._lock = threading.Lock()

    def parse(self, *, system: str, prompt: str, schema: type[T]) -> T:
        """system + prompt로 요청하고 schema 형태로 검증된 결과를 돌려준다."""
        key = self._cache_key(system, prompt, schema)
        if self._cache and (cached := self._cache.get(key)) is not None:
            with self._lock:
                self.usage.cached_calls += 1
            return schema.model_validate(cached)

        result, input_tokens, output_tokens = self._call(system, prompt, schema)
        with self._lock:
            self.usage.calls += 1
            self.usage.input_tokens += input_tokens
            self.usage.output_tokens += output_tokens
        if self._cache:
            self._cache.put(key, result.model_dump(mode="json"))
        return result

    def _call(self, system: str, prompt: str, schema: type[T]) -> tuple[T, int, int]:
        raise NotImplementedError

    def _cache_key(self, system: str, prompt: str, schema: type[BaseModel]) -> str:
        payload = json.dumps(
            [self.provider, self.model, system, prompt, schema.model_json_schema()], ensure_ascii=False, sort_keys=True
        )
        return hashlib.sha256(payload.encode()).hexdigest()


# ----------------------------------------------------------------------
# Gemini (기본값, 무료 등급)
# ----------------------------------------------------------------------


class GeminiLLM(BaseLLM):
    provider = "gemini"
    MAX_RETRIES = 4  # 분당 한도(429)에 걸리면 기다렸다 다시 시도하는 횟수
    BUSY_RETRIES = 3  # 서버 혼잡·오류(5xx)일 때 같은 모델로 다시 시도하는 횟수 (5·10·20초 간격)
    _BUSY = {500, 502, 503, 504}

    def __init__(self, settings: Settings, cache: LLMCache | None):
        super().__init__(settings, cache)
        from google import genai  # 쓰는 제공자의 SDK만 불러온다

        if not settings.gemini_api_key:
            raise LLMError(
                "Gemini API 키가 없습니다. aistudio.google.com → Get API key에서 무료 키를 만들어 "
                ".env의 GEMINI_API_KEY에 넣어 주세요."
            )
        self._client = genai.Client(api_key=settings.gemini_api_key)
        # 기본 모델이 계속 혼잡하면 바꿔서 시도할 모델 (같으면 바꾸지 않는다)
        fallback = settings.llm_fallback_model
        self._models = [self.model] + ([fallback] if fallback and fallback != self.model else [])

    def _call(self, system: str, prompt: str, schema: type[T]) -> tuple[T, int, int]:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
        )
        response = self._generate(prompt, config)

        if not response.text:
            raise LLMError("Gemini가 빈 응답을 보냈습니다 (안전 필터에 걸렸을 수 있습니다). 다시 시도해 보세요.")
        try:
            result = schema.model_validate_json(response.text)
        except ValidationError as e:
            # 형식은 JSON이어도 스키마와 다를 수 있다 (문서: 값의 정확성은 보장하지 않음)
            raise LLMError(f"Gemini 응답이 예상한 형식과 다릅니다. 다시 실행해 보세요. ({e.error_count()}개 항목 오류)") from e
        meta = response.usage_metadata
        return result, (meta.prompt_token_count or 0) if meta else 0, (meta.candidates_token_count or 0) if meta else 0

    def _generate(self, prompt: str, config):
        """일시적인 오류는 기다렸다 다시 시도하고, 기본 모델이 계속 혼잡하면 대체 모델로 바꾼다.

        - 429 분당 한도: 서버가 알려준 시간만큼 쉬고 같은 모델로 다시 (하루 한도는 바로 실패)
        - 5xx 혼잡·서버 오류: 5·10·20초 쉬고 다시, 그래도 안 되면 다음 모델로
        """
        from google.genai import errors

        last_error = None
        for model in self._models:
            rate_tries = busy_tries = 0
            while True:
                try:
                    response = self._client.models.generate_content(model=model, contents=prompt, config=config)
                    if model != self.model:
                        with self._lock:
                            self.usage.model = f"{self.provider}/{self.model} (혼잡해서 일부 {model} 사용)"
                    return response
                except errors.APIError as e:
                    text = str(e)
                    if e.code == 429 and "PerDay" not in text and rate_tries < self.MAX_RETRIES:
                        hint = re.search(r"retry(?:Delay| in)\D*(\d+(?:\.\d+)?)\s*s", text)
                        time.sleep(float(hint.group(1)) + 1 if hint else 15 * 2**rate_tries)
                        rate_tries += 1
                        continue
                    if e.code in self._BUSY:
                        if busy_tries < self.BUSY_RETRIES:
                            time.sleep(5 * 2**busy_tries)
                            busy_tries += 1
                            continue
                        last_error = e
                        break  # 이 모델은 계속 혼잡 → 다음 모델
                    raise _gemini_error(e, model) from e
                except Exception as e:  # 네트워크 오류 등
                    raise LLMError(f"Gemini API에 연결할 수 없습니다: {e}") from e
        raise _gemini_error(last_error, self.model) from last_error


def _gemini_error(e, model: str) -> LLMError:
    text = str(e)
    if e.code == 429:
        if "PerDay" in text:
            return LLMError(
                "Gemini 무료 등급의 하루 사용량을 다 썼습니다. 미국 태평양 시간 자정(한국 시간 오후 4~5시)에 초기화됩니다. "
                "이미 분석한 그룹은 캐시에 저장돼 있어서 내일 이어서 실행하면 남은 부분만 호출합니다."
            )
        return LLMError("Gemini 분당 사용 한도에 계속 걸립니다. 1~2분 뒤에 다시 시도하세요.")
    if e.code in (500, 502, 503, 504):
        return LLMError(
            "Gemini 서버가 지금 혼잡합니다 (Google 쪽 일시적인 문제). 몇 분 뒤 다시 시도하세요. "
            "이미 끝난 부분은 저장돼 있어서 다시 실행하면 이어서 진행합니다."
        )
    if e.code in (401, 403):
        return LLMError("GEMINI_API_KEY가 유효하지 않거나 권한이 없습니다. AI Studio에서 키를 확인하세요.")
    if e.code == 404:
        return LLMError(f"Gemini 모델 {model!r}을 찾을 수 없습니다. .env의 LLM_MODEL을 확인하세요.")
    return LLMError(f"Gemini API 오류 ({e.code}): {getattr(e, 'message', text)}")


# ----------------------------------------------------------------------
# Claude (선택, 유료)
# ----------------------------------------------------------------------

# 안전 분류기가 거절하면 서버가 다른 모델로 자동 재시도하는 기능(fallbacks)을 받는 모델
_CLAUDE_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1"}


class ClaudeLLM(BaseLLM):
    provider = "claude"

    def __init__(self, settings: Settings, cache: LLMCache | None):
        super().__init__(settings, cache)
        import anthropic

        self._anthropic = anthropic
        self.effort = settings.llm_effort
        try:
            kwargs = {"api_key": settings.anthropic_api_key} if settings.anthropic_api_key else {}
            self._client = anthropic.Anthropic(max_retries=3, **kwargs)
        except anthropic.AnthropicError as e:
            raise LLMError(_CLAUDE_NO_KEY) from e

    def _call(self, system: str, prompt: str, schema: type[T]) -> tuple[T, int, int]:
        anthropic = self._anthropic
        kwargs = {}
        if self.model in _CLAUDE_FALLBACK_MODELS:
            kwargs = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        try:
            response = self._client.beta.messages.parse(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_format=schema,
                output_config={"effort": self.effort},
                **kwargs,
            )
        except anthropic.AuthenticationError as e:
            raise LLMError(_CLAUDE_NO_KEY) from e
        except anthropic.NotFoundError as e:
            raise LLMError(f"모델 {self.model!r}을 찾을 수 없습니다. .env의 LLM_MODEL을 확인하세요.") from e
        except anthropic.RateLimitError as e:
            raise LLMError("Claude API 사용 한도에 걸렸습니다. 잠시 후 다시 시도하세요.") from e
        except anthropic.APIStatusError as e:
            raise LLMError(f"Claude API 오류 ({e.status_code}): {e.message}") from e
        except anthropic.APIConnectionError as e:
            raise LLMError("Claude API에 연결할 수 없습니다. 인터넷 연결을 확인하세요.") from e

        if response.stop_reason == "refusal":
            raise LLMError("Claude가 이 요청을 거절했습니다.")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise LLMError("Claude 응답이 길이 제한에 걸려 잘렸습니다. 분석 기간을 줄여서 다시 시도하세요.")
        return response.parsed_output, response.usage.input_tokens, response.usage.output_tokens


_CLAUDE_NO_KEY = (
    "Claude API 키가 없거나 유효하지 않습니다. console.anthropic.com → API Keys에서 키를 만들어 "
    ".env의 ANTHROPIC_API_KEY에 넣어 주세요."
)


def make_llm(settings: Settings, cache: LLMCache | None = None) -> BaseLLM:
    providers = {"gemini": GeminiLLM, "claude": ClaudeLLM}
    if settings.llm_provider not in providers:
        raise LLMError(f"LLM_PROVIDER는 {', '.join(providers)} 중 하나여야 합니다: {settings.llm_provider!r}")
    return providers[settings.llm_provider](settings, cache)
