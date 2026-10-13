import type { Outputs, Slide, Statement } from './types'

// 편집 도우미

/** 사용자가 새로 추가한 문장: 근거 커밋은 없고 '직접 수정' 표시만 */
export function newStatement(text = ''): Statement {
  return { text, evidence: [], from_readme: false, warnings: [], edited: true }
}

/** 문장 글을 바꾸면 '직접 수정' 표시를 붙이고, AI 검증 경고는 더 이상 맞지 않으니 지운다 */
export function editStatement<T extends Statement>(s: T, text: string): T {
  return { ...s, text, edited: true, warnings: [] }
}

/** 저장 전에 빈 항목을 정리한다 (지운 글, 빈 태그 등) */
export function cleanOutputs(o: Outputs): Outputs {
  const filled = (s: Statement) => s.text.trim() !== ''
  const words = (xs: string[]) => xs.map((x) => x.trim()).filter(Boolean)
  return {
    portfolio: {
      ...o.portfolio,
      contributions: o.portfolio.contributions
        .filter((c) => c.title.trim() || filled(c.summary))
        .map((c) => ({ ...c, points: c.points.filter(filled), technologies: words(c.technologies) })),
      tech_stack: o.portfolio.tech_stack
        .map((g) => ({ ...g, items: words(g.items) }))
        .filter((g) => g.category.trim() && g.items.length),
    },
    slides: o.slides.map(
      (s): Slide => ({
        ...s,
        points: s.points.filter((p) => p.heading.trim() || filled(p)),
        highlights: s.highlights.filter((h) => h.value.trim()),
        flow: words(s.flow),
      }),
    ),
  }
}
