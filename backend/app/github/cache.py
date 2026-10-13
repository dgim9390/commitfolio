"""GitHub API 응답을 저장하는 SQLite 캐시.

URL(쿼리 포함)을 키로 응답 본문과 ETag를 저장한다.
다음 요청 때 ETag를 If-None-Match로 보내서, 내용이 그대로면 GitHub가
본문 없이 304를 돌려주고 우리는 캐시 본문을 재사용한다.
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class CachedResponse:
    body: Any
    etag: str | None
    next_url: str | None  # 페이지네이션의 다음 페이지 (Link 헤더)
    fetched_at: datetime


class HttpCache:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(
            """CREATE TABLE IF NOT EXISTS http_cache (
                url        TEXT PRIMARY KEY,
                etag       TEXT,
                next_url   TEXT,
                body       TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )"""
        )
        self._conn.commit()

    def get(self, url: str) -> CachedResponse | None:
        row = self._conn.execute(
            "SELECT body, etag, next_url, fetched_at FROM http_cache WHERE url = ?", (url,)
        ).fetchone()
        if row is None:
            return None
        body, etag, next_url, fetched_at = row
        return CachedResponse(json.loads(body), etag, next_url, datetime.fromisoformat(fetched_at))

    def put(self, url: str, body: Any, etag: str | None, next_url: str | None) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO http_cache VALUES (?, ?, ?, ?, ?)",
            (url, etag, next_url, json.dumps(body), datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
