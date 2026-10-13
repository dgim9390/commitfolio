"""로컬 git 클론에서 diff를 읽는다.

커밋별 diff를 REST로 받으면 커밋 1개당 API 1회가 들지만,
클론해 두면 횟수 제한 없이 빠르게 읽을 수 있고 큰 diff도 잘리지 않는다.
클론 폴더가 그대로 캐시 역할을 해서, 재분석 때는 fetch로 새 커밋만 받는다.
"""

import re
import subprocess
from datetime import date
from pathlib import Path

from app.errors import GitError
from app.models import FileChange


class LocalRepo:
    def __init__(self, path: Path):
        self.path = path

    @classmethod
    def ensure(cls, clone_url: str, dest: Path) -> "LocalRepo":
        """dest에 bare 클론이 없으면 만들고, 있으면 최신 상태로 fetch한다."""
        if dest.exists():
            _git(["fetch", "--quiet", "--prune", "origin", "+refs/heads/*:refs/heads/*"], cwd=dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            # bare: 작업 폴더 없이 git 데이터만 받는다 (diff 읽기엔 충분하고 용량이 적다)
            _git(["clone", "--bare", "--quiet", clone_url, str(dest)])
        return cls(dest)

    def ensure_commits(self, shas: list[str]) -> set[str]:
        """주어진 커밋이 로컬에 있는지 확인하고, 없으면 SHA로 직접 fetch를 시도한다.

        반환값: 끝내 찾지 못한 SHA 집합 (force-push로 사라진 커밋 등).
        """
        missing = [s for s in shas if not self._has_commit(s)]
        if missing:
            try:
                _git(["fetch", "--quiet", "origin", *missing], cwd=self.path)
            except GitError:
                pass
        return {s for s in missing if not self._has_commit(s)}

    def show_patch(self, sha: str) -> str:
        return _git(
            ["show", "--format=", "--patch", "-M", "--no-color", "--no-ext-diff", "--no-textconv", sha],
            cwd=self.path,
        )

    def count_commits(self, branch: str, since: date | None, until: date | None) -> int:
        args = ["rev-list", "--count", branch]
        if since:
            args.append(f"--since={since.isoformat()}T00:00:00Z")
        if until:
            args.append(f"--until={until.isoformat()}T23:59:59Z")
        return int(_git(args, cwd=self.path).strip())

    def _has_commit(self, sha: str) -> bool:
        try:
            _git(["cat-file", "-e", f"{sha}^{{commit}}"], cwd=self.path)
            return True
        except GitError:
            return False


def _git(args: list[str], cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            # quotePath=false: 한글 파일명을 \355\225... 같은 이스케이프 없이 그대로 출력
            ["git", "-c", "core.quotePath=false", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # 깨진 인코딩의 파일이 있어도 멈추지 않게
            check=True,
        )
    except FileNotFoundError as e:
        raise GitError("git이 설치되어 있지 않습니다") from e
    except subprocess.CalledProcessError as e:
        raise GitError(e.stderr.strip() or str(e)) from e
    return result.stdout


# ----------------------------------------------------------------------
# unified diff 파싱
# ----------------------------------------------------------------------

_DIFF_HEADER = re.compile(r"^diff --git a/(.*) b/(.*)$")


def parse_patch(text: str) -> list[FileChange]:
    """`git show --patch` 출력을 파일별 FileChange 목록으로 나눈다.

    한 파일 구간은 `diff --git` 줄로 시작하고, 첫 `@@` 전까지는 메타 정보(새 파일, 삭제,
    이름 변경, 바이너리 여부), `@@` 이후는 실제 변경 내용이다.
    """
    files: list[FileChange] = []
    current: FileChange | None = None
    hunk_lines: list[str] = []
    in_hunk = False

    def flush() -> None:
        if current is not None:
            current.patch = "\n".join(hunk_lines) if hunk_lines else None
            files.append(current)

    for line in text.splitlines():
        if line.startswith("diff --git "):
            flush()
            m = _DIFF_HEADER.match(line)
            # 경로에 " b/"가 들어간 특이한 경우엔 헤더 파싱이 틀릴 수 있지만,
            # 아래 ---/+++ 줄에서 정확한 경로로 다시 덮어쓴다
            current = FileChange(path=m.group(2) if m else line[len("diff --git ") :])
            hunk_lines = []
            in_hunk = False
            continue
        if current is None:
            continue

        if not in_hunk:
            if line.startswith("new file mode"):
                current.status = "added"
            elif line.startswith("deleted file mode"):
                current.status = "deleted"
            elif line.startswith("rename from "):
                current.status = "renamed"
                current.old_path = line[len("rename from ") :]
            elif line.startswith("rename to "):
                current.path = line[len("rename to ") :]
            elif line.startswith("Binary files ") or line == "GIT binary patch":
                current.is_binary = True
            elif line.startswith("+++ ") and line != "+++ /dev/null":
                current.path = line[len("+++ b/") :]
            elif line.startswith("@@"):
                in_hunk = True
                hunk_lines.append(line)
            continue

        # 헝크 안: 여기서 "---"로 시작하는 줄은 헤더가 아니라 "--"로 시작하던 줄의 삭제다
        hunk_lines.append(line)
        if line.startswith("+"):
            current.additions += 1
        elif line.startswith("-"):
            current.deletions += 1

    flush()
    return files
