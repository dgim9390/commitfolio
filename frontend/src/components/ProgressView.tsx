import type { Job } from '../types'
import { AlertIcon, CheckIcon } from './icons'

const STEPS: { key: string; label: string }[] = [
  { key: 'collect', label: 'GitHub에서 커밋·diff 수집' },
  { key: 'group', label: '커밋을 기능 단위로 묶기' },
  { key: 'summarize', label: 'AI로 작업 요약' },
  { key: 'generate', label: '포트폴리오·발표 자료 작성' },
  { key: 'validate', label: '근거 검증' },
]

const card = 'rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm backdrop-blur sm:p-6 dark:border-slate-800 dark:bg-slate-900/70'

export function ProgressView({ job, onRetry }: { job: Job | null; onRetry: () => void }) {
  if (job?.status === 'error') {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-5 sm:p-6 dark:border-red-900 dark:bg-red-950/40">
        <p className="flex items-center gap-2 font-semibold text-red-700 dark:text-red-300">
          <AlertIcon className="h-4 w-4" /> 분석하지 못했습니다
        </p>
        <p className="mt-2 text-sm leading-6 text-red-700/90 dark:text-red-200">{job.error}</p>
        <button onClick={onRetry} className="mt-4 rounded-lg bg-red-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-red-500">
          다시 시도
        </button>
      </div>
    )
  }

  const current = Math.max(0, STEPS.findIndex((s) => s.key === job?.stage))
  const percent = Math.round(((current + 0.5) / STEPS.length) * 100)

  return (
    <div className={card} aria-live="polite">
      <div className="mb-5 flex items-center justify-between text-sm">
        <span className="font-semibold">분석 중</span>
        <span className="text-slate-400 tabular-nums">{percent}%</span>
      </div>
      <div className="mb-6 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
        <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-700" style={{ width: `${percent}%` }} />
      </div>
      <ol className="space-y-3">
        {STEPS.map((step, i) => {
          const state = i < current ? 'done' : i === current ? 'active' : 'pending'
          return (
            <li key={step.key} className="flex items-center gap-3 text-sm">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                  state === 'done'
                    ? 'bg-emerald-500 text-white'
                    : state === 'active'
                      ? 'animate-spin border-2 border-indigo-500 border-t-transparent'
                      : 'border border-slate-300 dark:border-slate-700'
                }`}
              >
                {state === 'done' && <CheckIcon className="h-3.5 w-3.5" />}
              </span>
              <span className={state === 'pending' ? 'text-slate-400' : state === 'active' ? 'font-semibold' : ''}>{step.label}</span>
            </li>
          )
        })}
      </ol>
      <p className="mt-5 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500 dark:bg-slate-800/60">{job?.message ?? '시작하는 중…'}</p>
    </div>
  )
}
