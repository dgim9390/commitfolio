import type { CSSProperties } from 'react'
import type { CoverName, Design, FontName, PaletteName, SlideThemeName, SurfaceName } from './types'

/**
 * 디자인은 고정 테마가 아니라 네 축의 조합이다.
 *   색 계열(15) × 배경 톤(5) × 글꼴(4) × 표지 형식(4) = 1,200가지
 * AI가 레포 성격에 맞춰 축마다 하나씩 고르고, 사용자는 편집 모드에서 바꾼다.
 *
 * 색·글꼴은 모두 CSS 변수(--th-*)로 내려보내고, 그 변수를 읽는 클래스(.th-card 등)는
 * index.css에 한 번만 적혀 있다. 그래서 조합이 늘어도 SlideCard·PortfolioView는 그대로다.
 * (Tailwind는 코드에 그대로 적힌 클래스만 만들어 주므로 조합마다 클래스를 지어낼 수 없다)
 */

interface Palette {
  label: string
  base: string // 밝은 배경에서 쓰는 강조색
  onDark: string // 어두운 배경에서 쓰는 강조색 (대비 확보용으로 더 밝은 단계)
  deep: string // 표지 그라데이션 시작
  mid: string // 표지 그라데이션 끝
}

export const PALETTES: Record<PaletteName, Palette> = {
  indigo: { label: '인디고', base: '#4f46e5', onDark: '#a5b4fc', deep: '#1e1b4b', mid: '#7c3aed' },
  violet: { label: '바이올렛', base: '#7c3aed', onDark: '#c4b5fd', deep: '#2e1065', mid: '#a855f7' },
  blue: { label: '블루', base: '#2563eb', onDark: '#93c5fd', deep: '#172554', mid: '#3b82f6' },
  sky: { label: '스카이', base: '#0284c7', onDark: '#7dd3fc', deep: '#082f49', mid: '#0ea5e9' },
  cyan: { label: '시안', base: '#0891b2', onDark: '#67e8f9', deep: '#083344', mid: '#06b6d4' },
  teal: { label: '틸', base: '#0d9488', onDark: '#5eead4', deep: '#042f2e', mid: '#14b8a6' },
  emerald: { label: '에메랄드', base: '#059669', onDark: '#6ee7b7', deep: '#022c22', mid: '#10b981' },
  green: { label: '그린', base: '#16a34a', onDark: '#86efac', deep: '#052e16', mid: '#4ade80' },
  lime: { label: '라임', base: '#4d7c0f', onDark: '#bef264', deep: '#1a2e05', mid: '#84cc16' },
  amber: { label: '앰버', base: '#b45309', onDark: '#fcd34d', deep: '#451a03', mid: '#f59e0b' },
  orange: { label: '오렌지', base: '#ea580c', onDark: '#fdba74', deep: '#431407', mid: '#f97316' },
  rose: { label: '로즈', base: '#e11d48', onDark: '#fda4af', deep: '#4c0519', mid: '#f43f5e' },
  fuchsia: { label: '푸시아', base: '#c026d3', onDark: '#f0abfc', deep: '#4a044e', mid: '#e879f9' },
  slate: { label: '슬레이트', base: '#0f172a', onDark: '#cbd5e1', deep: '#020617', mid: '#334155' },
  stone: { label: '스톤', base: '#57534e', onDark: '#d6d3d1', deep: '#1c1917', mid: '#78716c' },
}

interface Surface {
  label: string
  dark: boolean // 근거 칩처럼 작은 요소의 색을 고를 때 쓴다
  page: string
  fg: string
  muted: string
  card: string
  border: string
}

export const SURFACES: Record<SurfaceName, Surface> = {
  light: { label: '화이트', dark: false, page: '#ffffff', fg: '#0f172a', muted: '#475569', card: '#f8fafc', border: '#e2e8f0' },
  // 틴트·보더는 강조색을 아주 조금 섞어서 색 계열에 따라 같이 바뀐다
  tint: {
    label: '틴트',
    dark: false,
    page: 'color-mix(in oklab, var(--th-accent) 7%, #fff)',
    fg: '#0f172a',
    muted: '#475569',
    card: '#ffffff',
    border: 'color-mix(in oklab, var(--th-accent) 22%, #fff)',
  },
  paper: { label: '페이퍼', dark: false, page: '#faf7f1', fg: '#1c1917', muted: '#57534e', card: '#ffffff', border: '#e3dbcc' },
  ink: { label: '잉크', dark: false, page: '#ffffff', fg: '#000000', muted: '#525252', card: '#f5f5f5', border: '#111111' },
  dark: { label: '다크', dark: true, page: '#0d1117', fg: '#e6edf6', muted: '#9aa7b8', card: 'rgba(255,255,255,.05)', border: 'rgba(255,255,255,.12)' },
}

export const FONTS: Record<FontName, { label: string; heading: string; weight: string; tracking: string }> = {
  sans: { label: '산세리프', heading: 'var(--font-sans)', weight: '700', tracking: '-0.02em' },
  serif: { label: '명조', heading: 'var(--font-serif)', weight: '700', tracking: '0' },
  mono: { label: '코드', heading: 'var(--font-mono)', weight: '700', tracking: '-0.01em' },
  display: { label: '디스플레이', heading: 'var(--font-sans)', weight: '900', tracking: '-0.04em' },
}

export const COVER_LABELS: Record<CoverName, string> = {
  glow: '빛번짐',
  terminal: '터미널',
  paper: '문서',
  mono: '블랙',
}

/** 표지는 본문과 다른 배경을 쓰므로 색을 따로 계산한다 */
function coverVars(cover: CoverName, p: Palette): Record<string, string> {
  if (cover === 'terminal') {
    return {
      '--th-cover': '#0b0f17',
      '--th-cover-fg': p.onDark,
      '--th-cover-sub': '#94a3b8',
      '--th-cover-label': p.onDark,
      '--th-cover-line': 'rgba(255,255,255,.12)',
      '--th-glow-a': `${p.onDark}1f`,
      '--th-glow-b': `${p.mid}1f`,
    }
  }
  if (cover === 'paper') {
    return {
      '--th-cover': 'color-mix(in oklab, var(--th-accent) 6%, #f3efe7)',
      '--th-cover-fg': '#1c1917',
      '--th-cover-sub': '#57534e',
      '--th-cover-label': p.base,
      '--th-cover-line': '#1c1917',
      '--th-glow-a': 'transparent',
      '--th-glow-b': 'transparent',
    }
  }
  if (cover === 'mono') {
    return {
      '--th-cover': '#0a0a0a',
      '--th-cover-fg': '#ffffff',
      '--th-cover-sub': '#d4d4d4',
      '--th-cover-label': p.onDark,
      '--th-cover-line': 'rgba(255,255,255,.25)',
      '--th-glow-a': 'transparent',
      '--th-glow-b': 'transparent',
    }
  }
  return {
    '--th-cover': `linear-gradient(135deg, ${p.deep} 0%, ${p.mid} 100%)`,
    '--th-cover-fg': '#ffffff',
    '--th-cover-sub': 'rgba(255,255,255,.85)',
    '--th-cover-label': 'rgba(255,255,255,.72)',
    '--th-cover-line': 'rgba(255,255,255,.22)',
    '--th-glow-a': `${p.onDark}4d`,
    '--th-glow-b': `${p.mid}40`,
  }
}

/** 디자인 한 벌 → CSS 변수. 테마가 적용되는 요소(슬라이드 한 장, 포트폴리오 전체)에 style로 건다 */
export function designVars(design: Design): CSSProperties {
  const d = normalize(design)
  const p = PALETTES[d.palette]
  const s = SURFACES[d.surface]
  const f = FONTS[d.font]
  const accent = s.dark ? p.onDark : p.base
  return {
    '--th-accent': accent,
    // 채움(막대·배지·숫자 카드): 밝은 배경에서는 그라데이션, 어두운 배경에서는 밝은 단색 + 어두운 글자
    '--th-fill': s.dark ? accent : `linear-gradient(135deg, ${p.base} 0%, ${p.mid} 100%)`,
    '--th-on-fill': s.dark ? s.page : '#ffffff',
    '--th-page': s.page,
    '--th-fg': s.fg,
    '--th-muted': s.muted,
    '--th-card': s.card,
    '--th-border': s.border,
    '--th-heading-font': f.heading,
    '--th-heading-weight': f.weight,
    '--th-heading-tracking': f.tracking,
    ...coverVars(d.cover, p),
  } as CSSProperties
}

/** 클래스 이름은 조합과 무관하게 고정이다 (색은 위 변수가 바꾼다) */
const CLASSES = {
  heading: 'th-heading',
  page: 'th-page',
  muted: 'th-muted',
  kicker: 'th-kicker',
  bar: 'th-fill',
  divider: 'th-divider',
  card: 'th-card',
  cardTitle: 'th-heading',
  number: 'th-number',
  badge: 'th-fill',
  bullet: 'th-bullet',
  check: 'th-fill',
  chip: 'th-chip',
  arrow: 'th-arrow',
  highlight: 'th-fill',
  highlightLabel: 'th-on-fill-muted',
  footer: 'th-footer',
  cover: {
    bg: 'th-cover',
    title: 'th-cover-title',
    sub: 'th-cover-sub',
    label: 'th-cover-label',
    line: 'th-cover-line',
    ring: 'th-cover-ring',
    fill: 'th-cover-fill',
    caret: 'th-cover-caret',
    dim: 'th-cover-dim',
    glowA: 'th-glow-a',
    glowB: 'th-glow-b',
  },
}

export interface Theme extends Omit<typeof CLASSES, 'cover'> {
  dark: boolean
  vars: CSSProperties
  cover: typeof CLASSES.cover & { style: CoverName }
}

export function resolveTheme(design: Design): Theme {
  const d = normalize(design)
  return {
    ...CLASSES,
    dark: SURFACES[d.surface].dark,
    vars: designVars(d),
    cover: { ...CLASSES.cover, style: d.cover },
  }
}

/** 예전 결과(테마 이름 하나만 저장된 것)와 편집 중 잘못된 값에 대비한 기본값 */
const DEFAULT: Design = { palette: 'indigo', surface: 'light', font: 'sans', cover: 'glow' }

export const PRESETS: Record<SlideThemeName, Design> = {
  aurora: DEFAULT,
  terminal: { palette: 'emerald', surface: 'dark', font: 'mono', cover: 'terminal' },
  paper: { palette: 'amber', surface: 'paper', font: 'serif', cover: 'paper' },
  sunset: { palette: 'orange', surface: 'light', font: 'sans', cover: 'glow' },
  ocean: { palette: 'cyan', surface: 'tint', font: 'sans', cover: 'glow' },
  mono: { palette: 'slate', surface: 'ink', font: 'display', cover: 'mono' },
  forest: { palette: 'green', surface: 'tint', font: 'sans', cover: 'glow' },
}

export const PRESET_LABELS: Record<SlideThemeName, string> = {
  aurora: '오로라',
  terminal: '터미널',
  paper: '페이퍼',
  sunset: '선셋',
  ocean: '오션',
  mono: '모노',
  forest: '포레스트',
}

function normalize(d: Design): Design {
  return {
    palette: PALETTES[d?.palette] ? d.palette : DEFAULT.palette,
    surface: SURFACES[d?.surface] ? d.surface : DEFAULT.surface,
    font: FONTS[d?.font] ? d.font : DEFAULT.font,
    cover: COVER_LABELS[d?.cover] ? d.cover : DEFAULT.cover,
  }
}

/** 결과에서 디자인 꺼내기. design이 없는 예전 결과는 테마 이름을 조합으로 바꿔 준다 */
export function designOf(outputs: { design?: Design | null; theme?: SlideThemeName | null }): Design {
  if (outputs.design) return normalize(outputs.design)
  return PRESETS[outputs.theme ?? 'aurora'] ?? DEFAULT
}

export function designLabel(d: Design): string {
  const n = normalize(d)
  return [PALETTES[n.palette].label, SURFACES[n.surface].label, FONTS[n.font].label, COVER_LABELS[n.cover]].join(' · ')
}
