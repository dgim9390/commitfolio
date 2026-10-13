import { useState } from 'react'
import { portfolioMarkdown, statementText } from '../format'
import type { AnalysisResult, Contribution } from '../types'
import { CopyButton } from './CopyButton'
import { Evidence } from './Evidence'
import { CheckIcon } from './icons'

export function PortfolioTab({ result }: { result: AnalysisResult }) {
  const p = result.outputs.portfolio
  const [withLinks, setWithLinks] = useState(true)

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap items-center justify-end gap-3">
        <label className="flex items-center gap-1.5 text-xs text-slate-500">
          <input type="checkbox" className="accent-indigo-600" checked={withLinks} onChange={(e) => setWithLinks(e.target.checked)} />
          복사할 때 근거 링크 포함
        </label>
        <CopyButton text={() => portfolioMarkdown(result, withLinks)} label="전체 복사 (마크다운)" primary />
      </div>

      {/* 개요: 한 줄 소개를 크게, 설명은 읽기 좋은 폭으로 */}
      <section>
        <p className="text-xs font-semibold tracking-[0.2em] text-indigo-600 dark:text-indigo-400">OVERVIEW</p>
        <h3 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">{p.tagline}</h3>
        <p className="mt-3 max-w-3xl text-[15px] leading-7 text-slate-600 dark:text-slate-300">{p.overview}</p>
      </section>

      <section>
        <SectionTitle label="KEY CONTRIBUTIONS" title="주요 기여" count={p.contributions.length} />
        <ol className="mt-4 space-y-4">
          {p.contributions.map((c, i) => (
            <ContributionCard key={i} c={c} index={i} result={result} withLinks={withLinks} />
          ))}
        </ol>
      </section>

      <section>
        <SectionTitle label="TECH STACK" title="기술 스택" />
        <dl className="mt-4 divide-y divide-slate-100 rounded-2xl border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
          {p.tech_stack.map((g) => (
            <div key={g.category} className="grid gap-2 px-5 py-3.5 sm:grid-cols-[160px_1fr] sm:items-center">
              <dt className="text-sm font-semibold text-slate-500">{g.category}</dt>
              <dd className="flex flex-wrap gap-1.5">
                {g.items.map((t) => (
                  <span key={t} className="rounded-md bg-slate-100 px-2 py-0.5 text-[13px] text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                    {t}
                  </span>
                ))}
              </dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  )
}

function SectionTitle({ label, title, count }: { label: string; title: string; count?: number }) {
  return (
    <div>
      <p className="text-xs font-semibold tracking-[0.2em] text-indigo-600 dark:text-indigo-400">{label}</p>
      <h3 className="mt-1 text-lg font-bold">
        {title} {count !== undefined && <span className="text-slate-400">{count}</span>}
      </h3>
    </div>
  )
}

function ContributionCard({ c, index, result, withLinks }: { c: Contribution; index: number; result: AnalysisResult; withLinks: boolean }) {
  const copyText = () =>
    [c.title, statementText(c.summary, result, withLinks), ...c.points.map((p) => `- ${statementText(p, result, withLinks)}`)].join('\n')

  return (
    <li className="group rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-indigo-200 hover:shadow-md hover:shadow-indigo-500/5 sm:p-6 dark:border-slate-800 dark:bg-slate-900/40 dark:hover:border-indigo-900">
      <div className="flex items-start gap-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-sm font-bold text-white">
          {String(index + 1).padStart(2, '0')}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <h4 className="text-lg leading-tight font-bold">{c.title}</h4>
            <CopyButton text={copyText} className="shrink-0 sm:opacity-0 sm:group-hover:opacity-100 sm:focus:opacity-100" />
          </div>
          <p className="mt-2 leading-7 text-slate-700 dark:text-slate-300">{c.summary.text}</p>
          <Evidence statement={c.summary} result={result} />

          {c.points.length > 0 && (
            <ul className="mt-4 space-y-3 border-t border-slate-100 pt-4 dark:border-slate-800">
              {c.points.map((p, i) => (
                <li key={i} className="flex gap-2.5">
                  <CheckIcon className="mt-1 h-4 w-4 shrink-0 text-indigo-500" />
                  <div className="min-w-0">
                    <p className="text-[15px] leading-6 text-slate-700 dark:text-slate-300">{p.text}</p>
                    <Evidence statement={p} result={result} />
                  </div>
                </li>
              ))}
            </ul>
          )}

          {c.technologies.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-1.5">
              {c.technologies.map((t) => (
                <span key={t} className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </li>
  )
}
