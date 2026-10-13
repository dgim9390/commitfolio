"""GitHub REST API 클라이언트.

역할: 인증 헤더, 캐시(ETag 조건부 요청), 페이지네이션, 레이트 리밋 감지.
수집 로직(무엇을 가져올지)은 collector.py에 있고, 여기는 '어떻게 가져올지'만 담당한다.
"""

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

import httpx

from app.errors import BadTokenError, CommitFolioError, GitHubApiError, RateLimitError
from app.github.cache import HttpCache
from app.models import ApiStats

API_BASE = "https://api.github.com"


class NotFoundError(CommitFolioError):
    """404. 호출한 쪽에서 상황에 맞는 메시지의 에러로 바꿔서 던진다."""


class GitHubClient:
    def __init__(self, token: str, cache: HttpCache):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "commitfolio",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._http = httpx.Client(base_url=API_BASE, headers=headers, timeout=30)
        self._cache = cache
        self.stats = ApiStats(authenticated=bool(token))

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        body, _ = self._request(self._url(path, params))
        return body

    def paginate(self, path: str, params: dict[str, Any] | None = None) -> Iterator[Any]:
        """목록 API의 모든 페이지를 순서대로 돌며 항목을 하나씩 내보낸다.

        제너레이터라서 호출한 쪽이 중간에 break하면 남은 페이지는 요청하지 않는다.
        """
        url: str | None = self._url(path, {"per_page": 100, **(params or {})})
        while url:
            body, url = self._request(url)
            yield from body

    def rate_limit(self) -> ApiStats:
        """현재 남은 호출 수 확인. /rate_limit 호출 자체는 한도에서 차감되지 않는다."""
        resp = self._http.get("/rate_limit")
        self._update_rate_stats(resp)
        if resp.status_code == 401:
            raise BadTokenError()
        return self.stats

    def close(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------

    def _url(self, path: str, params: dict[str, Any] | None) -> str:
        # 쿼리를 정렬해서 같은 요청이 항상 같은 캐시 키가 되게 한다
        query = sorted((k, v) for k, v in (params or {}).items() if v is not None)
        return str(httpx.URL(API_BASE + path, params=query))

    def _request(self, url: str) -> tuple[Any, str | None]:
        cached = self._cache.get(url)
        headers = {"If-None-Match": cached.etag} if cached and cached.etag else {}

        try:
            resp = self._http.get(url, headers=headers)
        except httpx.HTTPError as e:
            if cached:  # 네트워크가 끊겨도 캐시가 있으면 그걸로 진행
                return cached.body, cached.next_url
            raise CommitFolioError(f"GitHub에 연결할 수 없습니다: {e}") from e

        self.stats.requests += 1
        self._update_rate_stats(resp)

        if resp.status_code == 304 and cached:
            # 토큰이 있으면 304는 한도에서 차감되지 않는다 (토큰이 없으면 차감됨)
            self.stats.not_modified += 1
            return cached.body, cached.next_url
        if self._is_rate_limited(resp):
            raise RateLimitError(self.stats.rate_limit_reset, self.stats.authenticated)
        if resp.status_code == 401:
            raise BadTokenError()
        if resp.status_code == 404:
            raise NotFoundError(url)
        if resp.status_code >= 400:
            message = resp.json().get("message", resp.text) if resp.content else resp.reason_phrase
            raise GitHubApiError(resp.status_code, message)

        body = resp.json()
        next_url = resp.links.get("next", {}).get("url")
        self._cache.put(url, body, resp.headers.get("etag"), next_url)
        return body, next_url

    def _update_rate_stats(self, resp: httpx.Response) -> None:
        h = resp.headers
        if "x-ratelimit-remaining" in h:
            self.stats.rate_limit_limit = int(h["x-ratelimit-limit"])
            self.stats.rate_limit_remaining = int(h["x-ratelimit-remaining"])
            self.stats.rate_limit_reset = datetime.fromtimestamp(
                int(h["x-ratelimit-reset"]), tz=timezone.utc
            )

    @staticmethod
    def _is_rate_limited(resp: httpx.Response) -> bool:
        # 기본 한도 초과는 403/429 + remaining=0, 2차 한도(짧은 시간 과다 요청)는 retry-after로 온다
        if resp.status_code not in (403, 429):
            return False
        return (
            resp.headers.get("x-ratelimit-remaining") == "0"
            or "retry-after" in resp.headers
            or "rate limit" in resp.text.lower()
        )
