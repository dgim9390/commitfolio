import type { AnalysisResult, Statement } from '../types'
import { AlertIcon, GitHubIcon } from './icons'

/** 문장의 근거: 커밋 링크(짧은 SHA, 마우스를 올리면 커밋 제목) + README + 검증 경고 */
// surface: 칩이 놓이는 배경
// - app: 앱 화면 (앱의 밝은/어두운 모드를 따른다)
// - light / dark: 테마가 적용된 포트폴리오 페이지 (앱 모드와 상관없이 그 배경에 맞는 색)
const CHIP = {
  app: 'text-slate-500 ring-slate-200 hover:bg-indigo-50 hover:text-indigo-700 hover:ring-indigo-200 dark:text-slate-400 dark:ring-slate-700 dark:hover:bg-indigo-950 dark:hover:text-indigo-300',
  light: 'text-slate-500 ring-black/10 hover:bg-black/5 hover:text-slate-900',
  dark: 'text-slate-400 ring-white/15 hover:bg-white/10 hover:text-white',
}

export function Evidence({
  statement,
  result,
  surface = 'app',
}: {
  statement: Statement
  result: AnalysisResult
  surface?: keyof typeof CHIP
}) {
  const commits = new Map(result.commits.map((c) => [c.sha, c]))
  const chip = `inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 ring-1 ${CHIP[surface]}`
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
