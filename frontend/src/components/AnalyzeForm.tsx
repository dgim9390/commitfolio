import { useState } from 'react'
import type { AnalyzeRequest } from '../types'
import { GitHubIcon, SparkIcon } from './icons'

const REPO_RE = /github\.com\/([\w.-]+)\/[\w.-]+|^([\w.-]+)\/[\w.-]+$/

export function AnalyzeForm({
  disabled,
  initial,
  onSubmit,
}: {
  disabled: boolean
  initial?: AnalyzeRequest // 주소창의 ?job=으로 결과를 다시 열었을 때 입력값을 채우기 위해
  onSubmit: (req: AnalyzeRequest) => void
}) {
  const [repoUrl, setRepoUrl] = useState(initial?.repo_url ?? '')
  const [username, setUsername] = useState(initial?.username ?? '')
  const [showPeriod, setShowPeriod] = useState(!!(initial?.since || initial?.until))
  const [since, setSince] = useState(initial?.since ?? '')
  const [until, setUntil] = useState(initial?.until ?? '')

  // 아이디를 비워 두면 레포 주인으로 채운다 (개인 레포는 대부분 본인)
  function fillUsername() {
    if (username) return
    const m = repoUrl.trim().match(REPO_RE)
    const owner = m?.[1] ?? m?.[2]
    if (owner) setUsername(owner)
  }

  function submit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit({
      repo_url: repoUrl.trim(),
      username: username.trim(),
      ...(showPeriod && since ? { since } : {}),
      ...(showPeriod && until ? { until } : {}),
    })
  }

  const input =
    'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm shadow-sm outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/15 dark:border-slate-700 dark:bg-slate-900'
  const label = 'mb-1.5 block text-xs font-semibold text-slate-600 dark:text-slate-400'

  return (
    <form
      onSubmit={submit}
      className="space-y-4 rounded-2xl border border-white/60 bg-white/80 p-5 shadow-xl shadow-indigo-900/5 ring-1 ring-slate-200/70 backdrop-blur sm:p-6 dark:border-slate-800 dark:bg-slate-900/70 dark:ring-slate-800"
    >
      <div className="grid gap-4 sm:grid-cols-[1fr_190px]">
        <label className="block">
          <span className={label}>공개 레포 주소</span>
          <div className="relative">
            <GitHubIcon className="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              className={`${input} pl-10`}
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              onBlur={fillUsername}
              placeholder="https://github.com/owner/repo"
              required
            />
          </div>
        </label>
        <label className="block">
          <span className={label}>분석할 GitHub 아이디</span>
          <input className={input} value={username} onChange={(e) => setUsername(e.target.value)} placeholder="협업 레포면 본인 아이디" required />
        </label>
      </div>

      {showPeriod && (
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="block">
            <span className={label}>시작일</span>
            <input type="date" className={input} value={since} onChange={(e) => setSince(e.target.value)} />
          </label>
          <label className="block">
            <span className={label}>종료일</span>
            <input type="date" className={input} value={until} onChange={(e) => setUntil(e.target.value)} />
          </label>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <button type="button" onClick={() => setShowPeriod((v) => !v)} className="text-xs font-medium text-slate-500 hover:text-indigo-600">
          {showPeriod ? '기간 지정 끄기 (전체 기간)' : '+ 분석 기간 지정'}
        </button>
        <button
          type="submit"
          disabled={disabled}
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/25 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <SparkIcon />
          {disabled ? '분석 중…' : '분석하기'}
        </button>
      </div>
    </form>
  )
}
