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
  const lines = [`## ${r.repo.name}`, `**${p.tagline}**`, '', p.overview, '', '### 주요 기여']
  for (const c of p.contributions) {
    lines.push('', `#### ${c.title}`, statementText(c.summary, r, withLinks))
    lines.push(...c.points.map((pt) => `- ${statementText(pt, r, withLinks)}`))
    if (c.technologies.length) lines.push(`- 기술: ${c.technologies.join(', ')}`)
  }
  lines.push('', '### 기술 스택', ...p.tech_stack.map((g) => `- **${g.category}**: ${g.items.join(', ')}`))
  return lines.join('\n')
}

export function slideText(slide: Slide): string {
  return [
    slide.title,
    slide.headline,
    ...(slide.flow.length ? [slide.flow.join(' → ')] : []),
    ...slide.points.map((p) => `- ${p.heading}: ${p.text}`),
    ...slide.highlights.map((h) => `- ${h.value} ${h.label}`),
    '',
    `발표자 메모: ${slide.notes}`,
  ].join('\n')
}

export function slidesMarkdown(r: AnalysisResult): string {
  return r.outputs.slides
    .map((s, i) =>
      [
        `## ${i + 1}. ${s.title}`,
        `**${s.headline}**`,
        ...(s.flow.length ? ['', s.flow.join(' → ')] : []),
        '',
        ...s.points.map((p) => `- **${p.heading}** ${p.text}`),
        ...s.highlights.map((h) => `- **${h.value}** ${h.label}`),
        '',
        `> ${s.notes}`,
      ].join('\n'),
    )
    .join('\n\n')
}
