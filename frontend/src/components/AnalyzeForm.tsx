import { useState } from 'react'
import type { AnalyzeRequest } from '../types'

const REPO_RE = /github\.com\/([\w.-]+)\/[\w.-]+|^([\w.-]+)\/[\w.-]+$/

export function AnalyzeForm({ disabled, onSubmit }: { disabled: boolean; onSubmit: (req: AnalyzeRequest) => void }) {
  const [repoUrl, setRepoUrl] = useState('')
  const [username, setUsername] = useState('')
  const [showPeriod, setShowPeriod] = useState(false)
  const [since, setSince] = useState('')
  const [until, setUntil] = useState('')

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
    'w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-700 dark:bg-zinc-950'

  return (
    <form onSubmit={submit} className="space-y-3 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="grid gap-3 sm:grid-cols-[1fr_200px]">
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-zinc-500">공개 레포 주소</span>
          <input
            className={input}
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            onBlur={fillUsername}
            placeholder="https://github.com/owner/repo"
            required
          />
        </label>
        <label className="block">
          <span className="mb-1 block text-xs font-medium text-zinc-500">분석할 GitHub 아이디</span>
          <input className={input} value={username} onChange={(e) => setUsername(e.target.value)} placeholder="협업 레포면 본인 아이디" required />
        </label>
      </div>

      {showPeriod && (
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-zinc-500">시작일</span>
            <input type="date" className={input} value={since} onChange={(e) => setSince(e.target.value)} />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-zinc-500">종료일</span>
            <input type="date" className={input} value={until} onChange={(e) => setUntil(e.target.value)} />
          </label>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <button type="button" onClick={() => setShowPeriod((v) => !v)} className="text-xs text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200">
          {showPeriod ? '기간 지정 끄기 (전체 기간)' : '+ 분석 기간 지정'}
        </button>
        <button
          type="submit"
          disabled={disabled}
          className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {disabled ? '분석 중…' : '분석하기'}
        </button>
      </div>
    </form>
  )
}
