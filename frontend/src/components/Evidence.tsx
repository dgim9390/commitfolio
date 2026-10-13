import type { AnalysisResult, Statement } from '../types'

/** 문장의 근거: 커밋 링크(짧은 SHA, 마우스를 올리면 커밋 제목) + README + 검증 경고 */
export function Evidence({ statement, result }: { statement: Statement; result: AnalysisResult }) {
  const commits = new Map(result.commits.map((c) => [c.sha, c]))
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs">
      <span className="text-zinc-400">근거</span>
      {statement.evidence.map((sha) => {
        const c = commits.get(sha)
        return (
          <a
            key={sha}
            href={c?.url}
            target="_blank"
            rel="noreferrer"
            title={c?.title}
            className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-zinc-600 hover:bg-indigo-100 hover:text-indigo-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-indigo-950 dark:hover:text-indigo-300"
          >
            {sha.slice(0, 7)}
          </a>
        )
      })}
      {statement.from_readme && (
        <a
          href={`${result.repo.url}#readme`}
          target="_blank"
          rel="noreferrer"
          className="rounded bg-zinc-100 px-1.5 py-0.5 text-zinc-600 hover:bg-indigo-100 dark:bg-zinc-800 dark:text-zinc-300"
        >
          README
        </a>
      )}
      {statement.warnings.map((w) => (
        <span key={w} className="text-amber-600 dark:text-amber-400">
          ⚠ {w}
        </span>
      ))}
    </div>
  )
}
