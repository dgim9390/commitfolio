import type { AnalysisResult } from './types'

/** 결과 머리말·표지에 쓰는 요약 정보 (기간, 커밋 수, 주요 언어) */
export function projectMeta(r: AnalysisResult) {
  const analyzed = new Set(r.summaries.flatMap((s) => s.evidence))
  const dates = r.commits
    .filter((c) => analyzed.has(c.sha))
    .map((c) => new Date(c.authored_at))
    .sort((a, b) => a.getTime() - b.getTime())
  const fmt = (d: Date) => `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`
  const period = dates.length ? `${fmt(dates[0])} – ${fmt(dates[dates.length - 1]).slice(5)}` : ''
  const total = Object.values(r.repo.languages).reduce((a, b) => a + b, 0) || 1
  const languages = Object.entries(r.repo.languages)
    .slice(0, 4)
    .map(([name, bytes]) => ({ name, share: bytes / total }))
  return { period, commits: analyzed.size, works: r.summaries.length, languages }
}
