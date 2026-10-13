import type { AnalysisResult, Slide, Statement } from './types'

// 복사용 텍스트 만들기. 노션·GitHub·이력서 편집기에 붙여 넣기 좋게 마크다운으로.

function evidenceLinks(s: Statement, r: AnalysisResult): string {
  const urls = new Map(r.commits.map((c) => [c.sha, c.url]))
  const refs = s.evidence.map((sha) => `[${sha.slice(0, 7)}](${urls.get(sha)})`)
  if (s.from_readme) refs.push(`[README](${r.repo.url}#readme)`)
  return refs.join(' ')
}

export function statementText(s: Statement, r: AnalysisResult, withLinks: boolean): string {
  return withLinks ? `${s.text} (근거: ${evidenceLinks(s, r)})` : s.text
}

export function portfolioMarkdown(r: AnalysisResult, withLinks: boolean): string {
  const p = r.outputs.portfolio
  return [
    `## ${r.repo.name}`,
    '',
    p.overview,
    '',
    '### 주요 기여',
    ...p.contributions.map((s) => `- ${statementText(s, r, withLinks)}`),
    '',
    '### 기술 스택',
    p.tech_stack.join(', '),
  ].join('\n')
}

export function slideText(slide: Slide): string {
  return [slide.title, ...slide.bullets.map((b) => `- ${b.text}`), '', `발표자 메모: ${slide.notes}`].join('\n')
}

export function slidesMarkdown(r: AnalysisResult): string {
  return r.outputs.slides
    .map((s, i) => [`## ${i + 1}. ${s.title}`, ...s.bullets.map((b) => `- ${b.text}`), '', `> ${s.notes}`].join('\n'))
    .join('\n\n')
}
