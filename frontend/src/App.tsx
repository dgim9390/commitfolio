import { useEffect, useState } from 'react'
import { getJob, startAnalysis } from './api'
import { AnalyzeForm } from './components/AnalyzeForm'
import { ProgressView } from './components/ProgressView'
import { ResultView } from './components/ResultView'
import type { AnalyzeRequest, Job } from './types'

const POLL_MS = 1000

// 결과 화면을 새로고침해도 유지되도록 작업 ID를 주소창(?job=...)에 둔다
function jobFromUrl(): string | null {
  return new URLSearchParams(window.location.search).get('job')
}

const FEATURES = ['모든 문장에 근거 커밋 링크', '근거 없는 수치는 경고', '발표 자료 PDF 저장']

export default function App() {
  const [jobId, setJobId] = useState<string | null>(jobFromUrl)
  const [job, setJob] = useState<Job | null>(null)
  const [requestError, setRequestError] = useState<string | null>(null)
  const [lastRequest, setLastRequest] = useState<AnalyzeRequest | null>(null)

  async function run(req: AnalyzeRequest) {
    setLastRequest(req)
    setRequestError(null)
    setJob(null)
    try {
      const { job_id } = await startAnalysis(req)
      setJobId(job_id)
      window.history.replaceState(null, '', `?job=${job_id}`)
    } catch (e) {
      setRequestError((e as Error).message)
    }
  }

  // 작업이 끝날 때까지 1초마다 상태를 물어본다
  useEffect(() => {
    if (!jobId) return
    let stopped = false
    async function poll() {
      try {
        const j = await getJob(jobId!)
        if (stopped) return
        setJob(j)
        if (j.status === 'done' || j.status === 'error') return
      } catch (e) {
        if (stopped) return
        setRequestError((e as Error).message)
        return
      }
      setTimeout(poll, POLL_MS)
    }
    poll()
    return () => {
      stopped = true
    }
  }, [jobId])

  const running = !!jobId && (!job || job.status === 'queued' || job.status === 'running')

  return (
    <div className="no-print relative min-h-screen overflow-x-hidden">
      {/* 배경 빛 번짐 */}
      <div className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[520px] bg-gradient-to-b from-indigo-100/80 via-violet-50/40 to-transparent dark:from-indigo-950/60 dark:via-violet-950/20" />
      <div className="pointer-events-none absolute top-[-120px] left-1/2 -z-10 h-[380px] w-[680px] -translate-x-1/2 rounded-full bg-violet-300/30 blur-3xl dark:bg-violet-700/20" />

      <main className="mx-auto max-w-5xl space-y-6 px-4 pt-14 pb-20 sm:pt-20">
        <header className="text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-200/70 bg-white/70 px-3 py-1 text-xs font-medium text-indigo-700 backdrop-blur dark:border-indigo-900 dark:bg-slate-900/60 dark:text-indigo-300">
            <span className="h-1.5 w-1.5 rounded-full bg-indigo-500" /> GitHub 커밋 → 포트폴리오 · 발표 자료
          </div>
          <h1 className="mt-5 text-4xl font-extrabold tracking-tight sm:text-5xl">
            Commit
            <span className="bg-gradient-to-r from-indigo-600 to-violet-500 bg-clip-text text-transparent">Folio</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-[15px] leading-7 text-slate-600 dark:text-slate-400">
            레포 주소만 넣으면 커밋과 코드 변경을 읽고, 근거가 확인된 내용으로만 포트폴리오 소개글과 발표 자료를 만듭니다.
          </p>
          <ul className="mt-5 flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs text-slate-500">
            {FEATURES.map((f) => (
              <li key={f} className="flex items-center gap-1.5">
                <span className="text-indigo-500">✓</span> {f}
              </li>
            ))}
          </ul>
        </header>

        <div className="mx-auto max-w-3xl space-y-4 pt-2">
          {/* key: 작업 정보가 도착하면 폼을 그 요청값으로 다시 그린다 */}
          <AnalyzeForm key={job?.id ?? "new"} initial={job?.request ?? lastRequest ?? undefined} disabled={running} onSubmit={run} />
          {requestError && (
            <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200 dark:bg-red-950/40 dark:text-red-300 dark:ring-red-900">
              {requestError}
            </p>
          )}
          {jobId && job?.status !== 'done' && !requestError && (
            <ProgressView job={job} onRetry={() => lastRequest && run(lastRequest)} />
          )}
        </div>

        {job?.status === 'done' && job.result && <ResultView job={job} onJobChange={setJob} />}
      </main>
    </div>
  )
}
