import { useState } from 'react'
import type { AnalysisResult } from '../types'
import { NotesTab } from './NotesTab'
import { PortfolioTab } from './PortfolioTab'
import { SlidesTab } from './SlidesTab'

const TABS = [
  { key: 'portfolio', label: '포트폴리오 소개글' },
  { key: 'slides', label: '발표 자료' },
  { key: 'notes', label: '근거·검증 메모' },
] as const
type TabKey = (typeof TABS)[number]['key']

export function ResultView({ result }: { result: AnalysisResult }) {
  const [tab, setTab] = useState<TabKey>('portfolio')
  const u = result.usage

  return (
    <div className="rounded-xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
      <div className="flex flex-wrap items-end justify-between gap-2 border-b border-zinc-200 px-5 pt-4 dark:border-zinc-800">
        <div className="pb-3">
          <a href={result.repo.url} target="_blank" rel="noreferrer" className="text-lg font-bold hover:underline">
            {result.repo.owner}/{result.repo.name}
          </a>
          <p className="text-xs text-zinc-500">
            {result.username}의 커밋 {result.summaries.reduce((n, s) => n + s.evidence.length, 0)}개 · 작업 {result.summaries.length}개 · AI 호출{' '}
            {u.calls}회{u.cached_calls ? ` (캐시 ${u.cached_calls}회)` : ''}
          </p>
        </div>
        <nav className="-mx-2 flex w-full gap-1 overflow-x-auto sm:mx-0 sm:w-auto" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={`-mb-px shrink-0 whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium ${
                tab === t.key ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400' : 'border-transparent text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>
      <div className="p-5">
        {tab === 'portfolio' && <PortfolioTab result={result} />}
        {tab === 'slides' && <SlidesTab result={result} />}
        {tab === 'notes' && <NotesTab result={result} />}
      </div>
    </div>
  )
}
