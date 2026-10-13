import { useState } from 'react'
import { projectMeta } from '../meta'
import type { AnalysisResult } from '../types'
import { GitHubIcon } from './icons'
import { NotesTab } from './NotesTab'
import { PortfolioTab } from './PortfolioTab'
import { SlidesTab } from './SlidesTab'

const TABS = [
  { key: 'portfolio', label: '포트폴리오' },
  { key: 'slides', label: '발표 자료' },
  { key: 'notes', label: '근거·검증' },
] as const
type TabKey = (typeof TABS)[number]['key']

const LANG_COLORS = ['bg-indigo-500', 'bg-violet-400', 'bg-sky-400', 'bg-slate-300']

export function ResultView({ result }: { result: AnalysisResult }) {
  const [tab, setTabState] = useState<TabKey>(() => {
    const fromUrl = new URLSearchParams(window.location.search).get('tab')
    return TABS.some((t) => t.key === fromUrl) ? (fromUrl as TabKey) : 'portfolio'
  })

  function setTab(key: TabKey) {
    setTabState(key)
    const params = new URLSearchParams(window.location.search)
    params.set('tab', key)
    window.history.replaceState(null, '', `?${params}`)
  }
  const m = projectMeta(result)
  const u = result.usage

  const stats = [
    { label: '분석 기간', value: m.period || '-' },
    { label: '분석한 커밋', value: `${m.commits}개` },
    { label: '기능 단위 작업', value: `${m.works}개` },
    { label: 'AI 호출', value: `${u.calls}회${u.cached_calls ? ` · 캐시 ${u.cached_calls}` : ''}` },
  ]

  return (
    <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5 dark:border-slate-800 dark:bg-slate-900/60">
      {/* 머리말: 레포 이름, 핵심 수치, 언어 비율 */}
      <div className="border-b border-slate-100 bg-gradient-to-br from-slate-50 to-indigo-50/60 px-5 pt-6 sm:px-8 dark:border-slate-800 dark:from-slate-900 dark:to-indigo-950/40">
        <a
          href={result.repo.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 text-xl font-bold tracking-tight hover:text-indigo-600 sm:text-2xl"
        >
          <GitHubIcon className="h-5 w-5" />
          {result.repo.owner}/{result.repo.name}
        </a>
        <p className="mt-1 text-sm text-slate-500">{result.username}의 기여 분석</p>

        <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl bg-white/80 px-3.5 py-2.5 ring-1 ring-slate-200/70 dark:bg-slate-900/70 dark:ring-slate-800">
              <dt className="text-[11px] font-medium text-slate-500">{s.label}</dt>
              <dd className="mt-0.5 text-sm font-semibold tabular-nums">{s.value}</dd>
            </div>
          ))}
        </dl>

        {m.languages.length > 0 && (
          <div className="mt-4">
            <div className="flex h-1.5 overflow-hidden rounded-full">
              {m.languages.map((l, i) => (
                <div key={l.name} className={LANG_COLORS[i]} style={{ width: `${l.share * 100}%` }} />
              ))}
            </div>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500">
              {m.languages.map((l, i) => (
                <span key={l.name} className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${LANG_COLORS[i]}`} />
                  {l.name} {Math.round(l.share * 100)}%
                </span>
              ))}
            </div>
          </div>
        )}

        <nav className="mt-5 -mb-px flex gap-1 overflow-x-auto" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={`shrink-0 border-b-2 px-4 py-2.5 text-sm font-semibold whitespace-nowrap transition ${
                tab === t.key
                  ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="p-5 sm:p-8">
        {tab === 'portfolio' && <PortfolioTab result={result} />}
        {tab === 'slides' && <SlidesTab result={result} />}
        {tab === 'notes' && <NotesTab result={result} />}
      </div>
    </section>
  )
}
