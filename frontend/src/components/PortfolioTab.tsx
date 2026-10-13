import { useState } from 'react'
import { portfolioMarkdown, statementText } from '../format'
import type { AnalysisResult } from '../types'
import { CopyButton } from './CopyButton'
import { Evidence } from './Evidence'

export function PortfolioTab({ result }: { result: AnalysisResult }) {
  const p = result.outputs.portfolio
  const [withLinks, setWithLinks] = useState(true)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-end gap-3">
        <label className="flex items-center gap-1.5 text-xs text-zinc-500">
          <input type="checkbox" checked={withLinks} onChange={(e) => setWithLinks(e.target.checked)} />
          복사할 때 근거 링크 포함
        </label>
        <CopyButton text={() => portfolioMarkdown(result, withLinks)} label="전체 복사 (마크다운)" />
      </div>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-zinc-500">프로젝트 개요</h3>
        <p className="leading-relaxed">{p.overview}</p>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-zinc-500">주요 기여</h3>
        <ul className="space-y-3">
          {p.contributions.map((s, i) => (
            <li key={i} className="group rounded-lg border border-zinc-200 p-3 dark:border-zinc-800">
              <div className="flex items-start justify-between gap-3">
                <p className="leading-relaxed">{s.text}</p>
                <CopyButton text={() => statementText(s, result, withLinks)} className="shrink-0 opacity-60 group-hover:opacity-100" />
              </div>
              <Evidence statement={s} result={result} />
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="mb-2 text-sm font-semibold text-zinc-500">기술 스택</h3>
        <div className="flex flex-wrap gap-1.5">
          {p.tech_stack.map((t) => (
            <span key={t} className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
              {t}
            </span>
          ))}
        </div>
      </section>
    </div>
  )
}
