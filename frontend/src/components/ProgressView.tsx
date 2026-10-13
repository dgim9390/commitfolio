import type { Job } from '../types'

const STEPS: { key: string; label: string }[] = [
  { key: 'collect', label: 'GitHub에서 커밋·diff 수집' },
  { key: 'group', label: '커밋을 기능 단위로 묶기' },
  { key: 'summarize', label: 'AI로 작업 요약' },
  { key: 'generate', label: '포트폴리오·발표 자료 작성' },
  { key: 'validate', label: '근거 검증' },
]

export function ProgressView({ job, onRetry }: { job: Job | null; onRetry: () => void }) {
  if (job?.status === 'error') {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-sm dark:border-red-900 dark:bg-red-950/40">
        <p className="font-semibold text-red-700 dark:text-red-300">분석하지 못했습니다</p>
        <p className="mt-1 text-red-700/90 dark:text-red-200">{job.error}</p>
        <button onClick={onRetry} className="mt-3 rounded-md bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500">
          다시 시도
        </button>
      </div>
    )
  }

  const current = STEPS.findIndex((s) => s.key === job?.stage)
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-950" aria-live="polite">
      <ol className="space-y-2.5">
        {STEPS.map((step, i) => {
          const state = current === -1 ? (i === 0 ? 'active' : 'pending') : i < current ? 'done' : i === current ? 'active' : 'pending'
          return (
            <li key={step.key} className="flex items-center gap-3 text-sm">
              <span
                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] ${
                  state === 'done'
                    ? 'bg-emerald-500 text-white'
                    : state === 'active'
                      ? 'border-2 border-indigo-500 border-t-transparent animate-spin'
                      : 'border border-zinc-300 dark:border-zinc-700'
                }`}
              >
                {state === 'done' ? '✓' : ''}
              </span>
              <span className={state === 'pending' ? 'text-zinc-400' : ''}>{step.label}</span>
            </li>
          )
        })}
      </ol>
      <p className="mt-4 text-xs text-zinc-500">{job?.message ?? '시작하는 중…'}</p>
    </div>
  )
}
