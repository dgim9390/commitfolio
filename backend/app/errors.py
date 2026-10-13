"""사용자에게 그대로 보여줄 수 있는 에러들.

CLI와 API는 CommitFolioError를 잡아서 str(e)를 화면에 표시한다.
그래서 메시지는 '무엇이 잘못됐고 어떻게 하면 되는지'를 한국어로 담는다.
"""

from datetime import datetime


class CommitFolioError(Exception):
    pass


class InvalidRepoUrlError(CommitFolioError):
    def __init__(self, url: str):
        super().__init__(
            f"GitHub 레포 주소 형식이 아닙니다: {url!r} "
            "(예: https://github.com/owner/repo)"
        )


class RepoNotFoundError(CommitFolioError):
    def __init__(self, full_name: str):
        super().__init__(
            f"레포 {full_name}를 찾을 수 없습니다. 주소가 맞는지, 공개 레포인지 확인하세요."
        )


class UserNotFoundError(CommitFolioError):
    def __init__(self, username: str):
        super().__init__(f"GitHub 사용자 {username!r}가 존재하지 않습니다.")


class RateLimitError(CommitFolioError):
    def __init__(self, reset_at: datetime | None, authenticated: bool):
        self.reset_at = reset_at
        self.authenticated = authenticated
        when = reset_at.astimezone().strftime("%H:%M") if reset_at else "잠시"
        msg = f"GitHub API 호출 한도를 다 썼습니다. {when} 이후에 다시 시도하세요."
        if not authenticated:
            msg += " .env에 GITHUB_TOKEN을 설정하면 한도가 시간당 60회에서 5000회로 늘어납니다."
        else:
            msg += " 이미 받은 데이터는 캐시에 남아 있어서 다시 실행하면 이어서 수집합니다."
        super().__init__(msg)


class BadTokenError(CommitFolioError):
    def __init__(self):
        super().__init__(
            "GITHUB_TOKEN이 유효하지 않습니다(만료 또는 오타). .env의 값을 확인하거나 비워 두세요."
        )


class GitHubApiError(CommitFolioError):
    def __init__(self, status: int, message: str):
        super().__init__(f"GitHub API 오류 ({status}): {message}")


class GitError(CommitFolioError):
    def __init__(self, message: str):
        super().__init__(f"git 명령 실행 실패: {message}")


class LLMError(CommitFolioError):
    """Claude API 호출 실패 (키 없음, 한도 초과, 거절 등)."""


class RepoTooLargeError(CommitFolioError):
    def __init__(self, full_name: str, size_mb: float, limit_mb: int):
        super().__init__(f"레포 {full_name}가 너무 큽니다 ({size_mb:.0f}MB, 상한 {limit_mb}MB). 더 작은 레포로 시도해 주세요.")


class TooManyCommitsError(CommitFolioError):
    def __init__(self, count: int, limit: int):
        super().__init__(
            f"분석할 커밋이 {count}개로 너무 많습니다 (상한 {limit}개). 시작일·종료일로 기간을 좁혀 주세요."
        )
