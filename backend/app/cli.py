"""터미널 실행용 CLI.

예) uv run commitfolio collect https://github.com/dgim9390/DeskBoard -u dgim9390
"""

from datetime import date
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from app.config import get_settings
from app.errors import CommitFolioError
from app.github.collector import collect as run_collect
from app.models import CollectResult
from app.pipeline.filters import REASON_LABELS

app = typer.Typer(no_args_is_help=True, help="CommitFolio: GitHub 커밋 분석 도구")
console = Console()


@app.callback()
def main() -> None:
    """서브커맨드 목록을 보여주기 위한 자리 (collect, 이후 group / generate 추가 예정)."""


def _parse_date(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise typer.BadParameter(f"날짜는 YYYY-MM-DD 형식이어야 합니다: {value}") from None


@app.command()
def collect(
    repo_url: str = typer.Argument(..., help="공개 레포 URL 또는 owner/repo"),
    user: str = typer.Option(..., "--user", "-u", help="분석할 GitHub 아이디"),
    since: str | None = typer.Option(None, help="시작일 YYYY-MM-DD (기본: 처음부터)"),
    until: str | None = typer.Option(None, help="종료일 YYYY-MM-DD (기본: 오늘까지)"),
    show: str | None = typer.Option(None, help="이 SHA(앞부분)의 필터링된 diff를 출력"),
    out: Path | None = typer.Option(None, help="결과 JSON 저장 경로 (기본: .cache/results/)"),
) -> None:
    """커밋·PR·diff를 수집하고 필터링한 결과를 보여준다."""
    settings = get_settings()
    try:
        with console.status("시작하는 중...") as status:
            result = run_collect(
                repo_url,
                user,
                _parse_date(since),
                _parse_date(until),
                settings,
                progress=lambda stage, msg: status.update(f"[{stage}] {msg}"),
            )
    except CommitFolioError as e:
        console.print(f"[bold red]오류:[/] {e}")
        raise typer.Exit(1) from None

    _print_summary(result)
    if show:
        _print_commit_diff(result, show)

    out = out or settings.cache_dir / "results" / f"{result.repo.owner}__{result.repo.name}__{user}.collect.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    console.print(f"\n결과 저장: [cyan]{out}[/]")


def _print_summary(r: CollectResult) -> None:
    s = r.stats
    period = f"{r.since or '처음'} ~ {r.until or '현재'}"
    console.rule(f"[bold]{r.repo.owner}/{r.repo.name}[/]  ·  {r.username}  ·  {period}")
    console.print(f"설명: {r.repo.description or '-'}")
    console.print(f"레포 언어(전체): {_top(r.repo.languages, 5)}")
    console.print(f"내가 바꾼 언어(줄 수): {_top(s.user_languages, 6)}")
    console.print(f"README: {'있음 (' + str(len(r.repo.readme)) + '자)' if r.repo.readme else '없음'}")
    console.print(
        f"커밋: 기간 내 레포 전체 {s.repo_commits_in_range}개 중 [bold]{s.user_commits}개[/] 매칭"
        f" (머지 커밋 {s.merge_commits}개는 diff 분석 제외)"
    )
    if s.repo_commits_in_range and s.user_commits < s.repo_commits_in_range * 0.5:
        console.print(
            "  [yellow]※ 본인 커밋이 더 있어야 한다면, 커밋 이메일이 GitHub 계정에 등록돼 있는지 확인하세요.[/]"
        )
    console.print(f"머지된 PR: {len(r.pull_requests)}개")
    reasons = ", ".join(f"{REASON_LABELS.get(k, k)} {v}" for k, v in s.excluded_by_reason.items()) or "없음"
    console.print(f"파일 변경: 총 {s.files_total}건, 제외 {s.files_excluded}건 ({reasons}), diff 잘림 {s.files_truncated}건")
    a = s.api
    console.print(
        f"GitHub API: 요청 {a.requests}회 (그중 캐시 재사용 304: {a.not_modified}회), "
        f"남은 한도 {a.rate_limit_remaining}/{a.rate_limit_limit}"
        + ("" if a.authenticated else " [yellow](토큰 없음)[/]")
    )

    table = Table(show_lines=False, header_style="bold")
    table.add_column("날짜", no_wrap=True)
    table.add_column("SHA", no_wrap=True)
    table.add_column("메시지")
    table.add_column("파일", justify="right", no_wrap=True)
    table.add_column("+/-", justify="right", no_wrap=True)
    table.add_column("diff 글자", justify="right", no_wrap=True)
    for c in r.commits:
        inc = c.included_files
        if c.is_merge:
            files, lines, chars = "머지", "", ""
        elif not c.diff_available:
            files, lines, chars = "[red]없음[/]", "", ""
        else:
            ex = len(c.files) - len(inc)
            files = f"{len(inc)}" + (f" [dim](+{ex}제외)[/]" if ex else "")
            lines = f"[green]+{sum(f.additions for f in inc)}[/]/[red]-{sum(f.deletions for f in inc)}[/]"
            n_chars = sum(len(f.patch or "") for f in inc)
            chars = f"{n_chars:,}" + ("[yellow]✂[/]" if any(f.truncated for f in inc) else "")
        pr = f" [magenta]#{c.pr_number}[/]" if c.pr_number else ""
        table.add_row(c.authored_at.astimezone().strftime("%m-%d %H:%M"), c.short_sha, c.title + pr, files, lines, chars)
    console.print(table)
    console.print("[dim]✂ = diff 길이 제한으로 일부 잘림[/]")


def _print_commit_diff(r: CollectResult, sha_prefix: str) -> None:
    matches = [c for c in r.commits if c.sha.startswith(sha_prefix)]
    if not matches:
        console.print(f"[red]{sha_prefix}로 시작하는 커밋이 없습니다.[/]")
        return
    c = matches[0]
    console.rule(f"{c.short_sha} {c.title}")
    console.print(c.url)
    for f in c.files:
        tag = f"[dim]제외: {REASON_LABELS.get(f.excluded_reason, f.excluded_reason)}[/]" if f.excluded_reason else ""
        console.print(f"\n[bold]{f.status:8} {f.path}[/] +{f.additions}/-{f.deletions} {tag}")
        if f.patch:
            console.print(f.patch, markup=False, highlight=False)


def _top(d: dict[str, int], n: int) -> str:
    total = sum(d.values()) or 1
    return ", ".join(f"{k} {v / total:.0%}" for k, v in list(d.items())[:n]) or "-"


if __name__ == "__main__":
    app()
