"""수집 단계: 레포 URL + 사용자 + 기간 → CollectResult.

데이터 출처를 섞어 쓴다 (1단계 설계 결정):
- REST API: 레포 정보, README, 언어, '이 사용자의 커밋 SHA 목록', 머지된 PR
  → GitHub 아이디 ↔ 커밋 이메일 매칭은 GitHub가 해 준다
- 로컬 git 클론: 커밋별 diff
  → 커밋 수와 무관하게 API 호출이 늘지 않는다
"""

import base64
import re
from collections import Counter
from collections.abc import Callable
from datetime import date, datetime, timezone

from app.config import Settings, get_settings
from app.errors import InvalidRepoUrlError, RateLimitError, RepoNotFoundError, UserNotFoundError
from app.github.cache import HttpCache
from app.github.client import GitHubClient, NotFoundError
from app.github.local_repo import LocalRepo, parse_patch
from app.models import CollectResult, CollectStats, Commit, PullRequest, RepoInfo
from app.pipeline.filters import apply_filters, user_languages

# (단계 이름, 메시지)를 받는 진행 상황 콜백. CLI는 출력하고, API는 작업 상태에 기록한다.
ProgressFn = Callable[[str, str], None]

# 레포 정보·언어·README·커밋 목록·PR 목록에 최소한 필요한 호출 수
MIN_REQUIRED_CALLS = 5

_REPO_URL = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?(?:/.*)?$"
)
_SHORT_FORM = re.compile(r"^([\w.-]+)/([\w.-]+)$")


def parse_repo_url(url: str) -> tuple[str, str]:
    """'https://github.com/owner/repo(.git)(/tree/...)' 또는 'owner/repo' → (owner, repo)"""
    url = url.strip()
    m = _REPO_URL.match(url) or _SHORT_FORM.match(url)
    if not m:
        raise InvalidRepoUrlError(url)
    return m.group(1), m.group(2)


def collect(
    repo_url: str,
    username: str,
    since: date | None = None,
    until: date | None = None,
    settings: Settings | None = None,
    progress: ProgressFn | None = None,
) -> CollectResult:
    settings = settings or get_settings()
    report = progress or (lambda stage, msg: None)
    owner, name = parse_repo_url(repo_url)

    cache = HttpCache(settings.cache_dir / "github.sqlite3")
    client = GitHubClient(settings.github_token, cache)
    try:
        # 1) 시작 전에 남은 호출 수 확인 → 도중에 막히는 것보다 미리 알려주는 게 낫다
        rate = client.rate_limit()
        if rate.rate_limit_remaining is not None and rate.rate_limit_remaining < MIN_REQUIRED_CALLS:
            raise RateLimitError(rate.rate_limit_reset, rate.authenticated)

        report("repo", f"{owner}/{name} 정보 가져오는 중")
        repo = _fetch_repo_info(client, owner, name)

        report("commits", f"{username}의 커밋 목록 가져오는 중")
        commits = _fetch_user_commits(client, repo, username, since, until)

        report("pulls", "머지된 PR 가져오는 중")
        prs = _fetch_merged_prs(client, repo, username, since, until)
        _link_commits_to_prs(commits, prs)

        report("clone", "레포 클론/업데이트 중 (diff 읽기용)")
        local = LocalRepo.ensure(
            f"https://github.com/{owner}/{name}.git",
            settings.cache_dir / "repos" / f"{owner}__{name}.git",
        )
        repo_commits_in_range = local.count_commits(repo.default_branch, since, until)

        targets = [c for c in commits if not c.is_merge]
        missing = local.ensure_commits([c.sha for c in targets])
        for i, c in enumerate(targets, 1):
            report("diffs", f"diff 읽는 중 ({i}/{len(targets)})")
            if c.sha in missing:
                c.diff_available = False
                continue
            c.files = parse_patch(local.show_patch(c.sha))

        report("filter", "불필요한 파일 제외, diff 길이 제한 적용 중")
        apply_filters(commits, settings)

        all_files = [f for c in commits for f in c.files]
        excluded = Counter(f.excluded_reason for f in all_files if f.excluded_reason)
        stats = CollectStats(
            repo_commits_in_range=repo_commits_in_range,
            user_commits=len(commits),
            merge_commits=sum(c.is_merge for c in commits),
            files_total=len(all_files),
            files_excluded=sum(excluded.values()),
            excluded_by_reason=dict(excluded.most_common()),
            files_truncated=sum(f.truncated for f in all_files),
            user_languages=user_languages(commits),
            api=client.stats,
        )
        return CollectResult(
            repo=repo,
            username=username,
            since=since,
            until=until,
            commits=commits,
            pull_requests=prs,
            stats=stats,
            collected_at=datetime.now(timezone.utc),
        )
    finally:
        client.close()
        cache.close()


# ----------------------------------------------------------------------


def _fetch_repo_info(client: GitHubClient, owner: str, name: str) -> RepoInfo:
    try:
        meta = client.get(f"/repos/{owner}/{name}")
    except NotFoundError:
        raise RepoNotFoundError(f"{owner}/{name}") from None

    # GitHub는 대소문자를 바꿔 넣어도 찾아 주므로, 이후 요청엔 정식 이름을 쓴다
    owner, name = meta["owner"]["login"], meta["name"]
    languages = client.get(f"/repos/{owner}/{name}/languages")
    try:
        readme_json = client.get(f"/repos/{owner}/{name}/readme")
        readme = base64.b64decode(readme_json["content"]).decode("utf-8", errors="replace")
    except NotFoundError:
        readme = None

    return RepoInfo(
        owner=owner,
        name=name,
        url=meta["html_url"],
        description=meta.get("description"),
        default_branch=meta["default_branch"],
        topics=meta.get("topics", []),
        languages=languages,
        readme=readme,
    )


def _fetch_user_commits(
    client: GitHubClient, repo: RepoInfo, username: str, since: date | None, until: date | None
) -> list[Commit]:
    params = {
        "author": username,  # GitHub 아이디로 필터 (계정에 연결된 이메일의 커밋이 잡힘)
        "since": f"{since.isoformat()}T00:00:00Z" if since else None,
        "until": f"{until.isoformat()}T23:59:59Z" if until else None,
    }
    items = list(client.paginate(f"/repos/{repo.owner}/{repo.name}/commits", params))

    if not items:
        # 커밋이 0개면 아이디 오타인지 확인해서 더 정확한 메시지를 준다
        try:
            client.get(f"/users/{username}")
        except NotFoundError:
            raise UserNotFoundError(username) from None

    commits = [
        Commit(
            sha=it["sha"],
            url=it["html_url"],
            message=it["commit"]["message"],
            authored_at=it["commit"]["author"]["date"],
            author_login=(it.get("author") or {}).get("login"),
            is_merge=len(it["parents"]) > 1,
        )
        for it in items
    ]
    commits.sort(key=lambda c: c.authored_at)  # API는 최신순 → 오래된 순으로
    return commits


def _fetch_merged_prs(
    client: GitHubClient, repo: RepoInfo, username: str, since: date | None, until: date | None
) -> list[PullRequest]:
    base = f"/repos/{repo.owner}/{repo.name}"
    since_dt = datetime.combine(since, datetime.min.time(), timezone.utc) if since else None
    until_dt = datetime.combine(until, datetime.max.time(), timezone.utc) if until else None

    prs: list[PullRequest] = []
    # 최근 수정순으로 받다가 기간 시작보다 오래된 PR이 나오면 멈춘다 (큰 레포에서 호출 절약)
    params = {"state": "closed", "sort": "updated", "direction": "desc"}
    for it in client.paginate(f"{base}/pulls", params):
        updated = datetime.fromisoformat(it["updated_at"])
        if since_dt and updated < since_dt:
            break
        if not it.get("merged_at") or (it.get("user") or {}).get("login", "").lower() != username.lower():
            continue
        merged = datetime.fromisoformat(it["merged_at"])
        if (since_dt and merged < since_dt) or (until_dt and merged > until_dt):
            continue
        shas = [c["sha"] for c in client.paginate(f"{base}/pulls/{it['number']}/commits")]
        # squash merge면 기본 브랜치에는 PR 커밋 대신 merge_commit_sha 하나만 남는다
        if it.get("merge_commit_sha") and it["merge_commit_sha"] not in shas:
            shas.append(it["merge_commit_sha"])
        prs.append(
            PullRequest(
                number=it["number"],
                title=it["title"],
                body=it.get("body") or "",
                url=it["html_url"],
                merged_at=merged,
                commit_shas=shas,
            )
        )
    prs.sort(key=lambda p: p.merged_at)
    return prs


def _link_commits_to_prs(commits: list[Commit], prs: list[PullRequest]) -> None:
    sha_to_pr = {sha: pr.number for pr in prs for sha in pr.commit_shas}
    for c in commits:
        c.pr_number = sha_to_pr.get(c.sha)
