"""여러 단계에서 같이 쓰는 텍스트·커밋 ID 도우미."""

import re

from app.models import Commit

# 커밋 끝의 서명 줄 (Co-Authored-By:, Signed-off-by: 등) → 작업 내용과 무관
_TRAILER = re.compile(r"^[A-Za-z-]+-by:.*$", re.MULTILINE | re.IGNORECASE)


def strip_trailers(message: str) -> str:
    return _TRAILER.sub("", message).strip()


class CommitIndex:
    """LLM에게는 40자리 SHA 대신 짧은 ID(C01, C02 ...)를 보여준다.

    긴 SHA는 LLM이 옮겨 적다 틀리기 쉽고 토큰도 많이 든다. 짧은 ID는 틀리면
    바로 '없는 ID'로 걸러낼 수 있어서 검증이 쉽다.
    """

    def __init__(self, commits: list[Commit]):
        ordered = sorted(commits, key=lambda c: c.authored_at)
        width = max(2, len(str(len(ordered))))
        self._id_to_sha = {f"C{i:0{width}d}": c.sha for i, c in enumerate(ordered, 1)}
        self._sha_to_id = {sha: cid for cid, sha in self._id_to_sha.items()}

    def id_of(self, sha: str) -> str:
        return self._sha_to_id[sha]

    def sha_of(self, commit_id: str) -> str | None:
        return self._id_to_sha.get(commit_id.strip().upper())
