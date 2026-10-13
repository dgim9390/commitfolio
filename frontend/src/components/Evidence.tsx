import type { AnalysisResult, Statement } from '../types'
import { AlertIcon, GitHubIcon } from './icons'

/** 문장의 근거: 커밋 링크(짧은 SHA, 마우스를 올리면 커밋 제목) + README + 검증 경고 */
export function Evidence({ statement, result }: { statement: Statement; result: AnalysisResult }) {
  const commits = new Map(result.commits.map((c) => [c.sha, c]))
  const chip =
    'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-slate-500 ring-1 ring-slate-200 hover:bg-indigo-50 hover:text-indigo-700 hover:ring-indigo-200 dark:text-slate-400 dark:ring-slate-700 dark:hover:bg-indigo-950 dark:hover:text-indigo-300'
  return (
    <div className="mt-1.5 flex flex-wrap items-center gap-1 text-[11px]">
      {/* 사용자가 고친 문장은 AI가 근거로 확인한 문장과 구분해서 보여준다 */}
      {statement.edited && (
        <span className="rounded-md bg-indigo-50 px-1.5 py-0.5 font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
          {statement.evidence.length || statement.from_readme ? '직접 수정' : '직접 추가'}
        </span>
      )}
      {statement.evidence.map((sha) => {
        const c = commits.get(sha)
        return (
          <a key={sha} href={c?.url} target="_blank" rel="noreferrer" title={c?.title} className={`${chip} font-mono`}>
            <GitHubIcon className="h-3 w-3" />
            {sha.slice(0, 7)}
          </a>
        )
      })}
      {statement.from_readme && (
        <a href={`${result.repo.url}#readme`} target="_blank" rel="noreferrer" className={chip}>
          README
        </a>
      )}
      {statement.warnings.map((w) => (
        <span key={w} className="inline-flex items-center gap-1 rounded-md bg-amber-50 px-1.5 py-0.5 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
          <AlertIcon className="h-3 w-3" /> {w}
        </span>
      ))}
    </div>
  )
}
