import { useEffect, useRef, useState } from 'react'
import { getJob, startAnalysis } from './api'
import { AnalyzeForm } from './components/AnalyzeForm'
import { ProgressView } from './components/ProgressView'
import { ResultView } from './components/ResultView'
import type { AnalyzeRequest, Job } from './types'

const POLL_MS = 1000

export default function App() {
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const [requestError, setRequestError] = useState<string | null>(null)
  const lastRequest = useRef<AnalyzeRequest | null>(null)

  async function run(req: AnalyzeRequest) {
    lastRequest.current = req
    setRequestError(null)
    setJob(null)
    try {
      const { job_id } = await startAnalysis(req)
      setJobId(job_id)
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
    <div className="min-h-screen">
      <main className="no-print mx-auto max-w-4xl space-y-5 px-4 py-10">
        <header>
          <h1 className="text-2xl font-bold tracking-tight">
            Commit<span className="text-indigo-600">Folio</span>
          </h1>
          <p className="mt-1 text-sm text-zinc-500">
            GitHub 레포의 커밋을 읽고 포트폴리오 소개글과 발표 자료를 만듭니다. 모든 문장에는 근거가 된 커밋이 붙습니다.
          </p>
        </header>

        <AnalyzeForm disabled={running} onSubmit={run} />

        {requestError && (
          <p className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">{requestError}</p>
        )}
        {jobId && job?.status !== 'done' && !requestError && (
          <ProgressView job={job} onRetry={() => lastRequest.current && run(lastRequest.current)} />
        )}
        {job?.status === 'done' && job.result && <ResultView result={job.result} />}
      </main>
    </div>
  )
}
