"""사용자가 정한 그룹화 기준 중 '규칙'으로 딱 떨어지는 것들.

- 분석 제외: 문서만 바꾼 커밋, 버전 번호만 올린 커밋, 분석할 파일이 없는 커밋
- 이름표: 커밋 메시지 앞의 "이름:" 또는 "[이름]"이 같으면 무조건 같은 그룹

점수로 판단하는 부분(유사도)은 heuristic.py에 있다.
"""

import re
from pathlib import PurePosixPath

from app.models import Commit, FileChange

# ----------------------------------------------------------------------
# 분석 제외
# ----------------------------------------------------------------------

EXCLUDE_LABELS = {
    "docs_only": "문서만 수정",
    "version_bump": "버전 번호만 변경",
    "no_code": "분석할 파일 없음",
}

_DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".adoc"}
_DOC_NAMES = {"license", "licence", "changelog", "authors", "contributors", "notice"}
# 버전 번호가 들어 있는 설정 파일
_MANIFESTS = {
    "package.json", "app.json", "app.config.json", "pyproject.toml", "setup.py", "setup.cfg",
    "cargo.toml", "pubspec.yaml", "build.gradle", "build.gradle.kts", "info.plist", "version",
    "version.txt", "manifest.json",
}  # fmt: skip
VERSION_BUMP_MAX_LINES = 6


def is_doc_file(path: str) -> bool:
    p = PurePosixPath(path)
    return (
        p.suffix.lower() in _DOC_SUFFIXES
        or p.stem.lower() in _DOC_NAMES
        or any(part.lower() in ("docs", "doc") for part in p.parts[:-1])
    )


def exclusion_reason(c: Commit) -> str | None:
    """이 커밋을 그룹화·요약 대상에서 뺄 이유. 없으면 None."""
    if not c.diff_available:
        return None  # diff를 못 읽었을 뿐 실제 작업일 수 있으므로 남긴다
    files: list[FileChange] = c.included_files
    if not files:
        return "no_code"  # lock 파일, 이미지만 바뀐 경우 등
    if all(is_doc_file(f.path) for f in files):
        return "docs_only"
    if (
        all(PurePosixPath(f.path).name.lower() in _MANIFESTS for f in files)
        and sum(f.lines_changed for f in files) <= VERSION_BUMP_MAX_LINES
    ):
        return "version_bump"
    return None


# ----------------------------------------------------------------------
# 메시지 이름표
# ----------------------------------------------------------------------

# feat(auth): ... 같은 Conventional Commits. 'feat' 자체는 너무 흔하니 괄호 안 범위만 이름표로 쓴다
_CONVENTIONAL = re.compile(
    r"^(?:feat|fix|chore|docs|refactor|style|test|perf|build|ci|revert)(?:\(([^)]+)\))?!?:\s", re.IGNORECASE
)
# "[이름] ..." 또는 "이름: ..." (콜론 뒤 공백 필수 → https:// 같은 건 안 걸림)
_LABEL = re.compile(r"^\[([^\]\n]{1,20})\]\s|^([^:：\n\[]{1,20})[:：]\s")
_VERSION = re.compile(r"v?\d+(?:\.\d+)+")
# 이름표처럼 생겼지만 '같은 작업'이라는 뜻이 없는 것
_GENERIC_LABELS = {"fix", "update", "wip", "misc", "hotfix", "버그 수정", "수정", "기타", "리팩터링", "정리", "임시"}


def message_label(message: str) -> str | None:
    """'3D: 키보드 수정' → '3d'. 이름표가 없거나 너무 일반적이면 None.

    버전 번호는 지운다: '맥 앱 1.1.0:'과 '맥 앱 1.2.0:'은 같은 '맥 앱' 이름표.
    """
    title = message.split("\n", 1)[0].strip()
    m = _CONVENTIONAL.match(title)
    if m:
        raw = m.group(1)
    else:
        m = _LABEL.match(title)
        raw = (m.group(1) or m.group(2)) if m else None
    if not raw:
        return None
    label = " ".join(_VERSION.sub("", raw).lower().split())
    if not label or label in _GENERIC_LABELS:
        return None
    return label
