import type { SlideThemeName } from './types'

// 발표 자료 테마. 레이아웃(SlideCard)은 그대로 두고 색·글꼴·장식만 바꾼다.
// Tailwind는 코드에 그대로 적힌 클래스만 만들어 주므로, 클래스 이름을 문자열 조각으로
// 이어 붙이지 않고 완성된 형태로 적어 둔다.

export interface SlideTheme {
  label: string
  description: string
  cover: {
    style: 'glow' | 'terminal' | 'paper' | 'mono' // 표지 장식 방식
    bg: string
    title: string
    sub: string
    label: string
    glowA: string
    glowB: string
  }
  heading: string // 제목 글꼴
  page: string // 본문 장 배경·글자색
  muted: string
  kicker: string // 장 맨 위 작은 영문 표시(AGENDA, FEATURE 등)
  bar: string
  divider: string
  card: string
  cardTitle: string
  number: string
  badge: string // 문제 정의 번호 동그라미
  bullet: string // 기능 항목 왼쪽 선
  check: string
  chip: string // 흐름도 단계
  arrow: string
  highlight: string // 숫자 카드
  highlightLabel: string
  footer: string
}

export const SLIDE_THEMES: Record<SlideThemeName, SlideTheme> = {
  aurora: {
    label: '오로라',
    description: '보라 그라데이션 · 범용 웹·AI 서비스',
    cover: {
      style: 'glow',
      bg: 'bg-gradient-to-br from-indigo-950 via-indigo-700 to-violet-600 text-white',
      title: 'font-extrabold',
      sub: 'text-indigo-100',
      label: 'text-indigo-200',
      glowA: 'bg-violet-400/30',
      glowB: 'bg-indigo-400/20',
    },
    heading: 'font-sans font-bold tracking-tight',
    page: 'bg-white text-slate-900',
    muted: 'text-slate-600',
    kicker: 'text-indigo-600',
    bar: 'bg-gradient-to-r from-indigo-600 to-violet-500',
    divider: 'border-slate-200',
    card: 'bg-slate-50 ring-1 ring-slate-200',
    cardTitle: 'text-slate-900',
    number: 'text-indigo-300',
    badge: 'bg-indigo-600 text-white',
    bullet: 'border-indigo-500',
    check: 'bg-emerald-500 text-white',
    chip: 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200',
    arrow: 'text-indigo-300',
    highlight: 'bg-gradient-to-br from-indigo-600 to-violet-600 text-white',
    highlightLabel: 'text-indigo-100',
    footer: 'text-slate-400',
  },
  terminal: {
    label: '터미널',
    description: '어두운 화면 + 코드 글꼴 · 개발 도구·백엔드·CLI',
    cover: {
      style: 'terminal',
      bg: 'bg-[#0b0f17] text-slate-100',
      title: 'font-mono font-bold text-emerald-300',
      sub: 'text-slate-300',
      label: 'font-mono text-emerald-500/80',
      glowA: 'bg-emerald-500/10',
      glowB: 'bg-cyan-500/10',
    },
    heading: 'font-mono font-bold tracking-tight text-emerald-300',
    page: 'bg-[#0d1117] text-slate-100',
    muted: 'text-slate-400',
    kicker: 'font-mono text-emerald-400',
    bar: 'bg-emerald-400',
    divider: 'border-white/10',
    card: 'bg-white/[0.04] ring-1 ring-white/10',
    cardTitle: 'text-slate-100',
    number: 'font-mono text-emerald-500/50',
    badge: 'bg-emerald-400/15 font-mono text-emerald-300 ring-1 ring-emerald-400/40',
    bullet: 'border-emerald-400',
    check: 'bg-emerald-400 text-[#0d1117]',
    chip: 'bg-emerald-400/10 font-mono text-emerald-300 ring-1 ring-emerald-400/30',
    arrow: 'text-emerald-500',
    highlight: 'bg-emerald-400/10 text-emerald-200 ring-1 ring-emerald-400/40',
    highlightLabel: 'font-mono text-emerald-400/80',
    footer: 'font-mono text-slate-500',
  },
  paper: {
    label: '페이퍼',
    description: '종이 질감 + 명조체 · 문서·연구·교육·리포트',
    cover: {
      style: 'paper',
      bg: 'bg-[#f4efe6] text-stone-900',
      title: 'font-serif font-black',
      sub: 'font-serif text-stone-600',
      label: 'font-serif italic text-amber-800',
      glowA: '',
      glowB: '',
    },
    heading: 'font-serif font-bold',
    page: 'bg-[#faf7f1] text-stone-900',
    muted: 'text-stone-600',
    kicker: 'font-serif italic tracking-normal text-amber-800',
    bar: 'bg-amber-800',
    divider: 'border-stone-300',
    card: 'bg-white ring-1 ring-stone-200',
    cardTitle: 'font-serif text-stone-900',
    number: 'font-serif text-amber-800/40',
    badge: 'border border-amber-800 font-serif text-amber-800',
    bullet: 'border-amber-800',
    check: 'bg-amber-800 text-amber-50',
    chip: 'border border-stone-400 bg-white font-serif text-stone-800',
    arrow: 'text-stone-400',
    highlight: 'bg-stone-900 text-amber-50',
    highlightLabel: 'font-serif text-stone-300',
    footer: 'font-serif italic text-stone-400',
  },
  sunset: {
    label: '선셋',
    description: '주황·분홍 그라데이션 · 소비자 앱·라이프스타일',
    cover: {
      style: 'glow',
      bg: 'bg-gradient-to-br from-orange-500 via-rose-500 to-fuchsia-600 text-white',
      title: 'font-extrabold',
      sub: 'text-orange-50',
      label: 'text-orange-100',
      glowA: 'bg-yellow-300/30',
      glowB: 'bg-fuchsia-300/25',
    },
    heading: 'font-sans font-extrabold tracking-tight',
    page: 'bg-white text-stone-900',
    muted: 'text-stone-600',
    kicker: 'text-rose-500',
    bar: 'bg-gradient-to-r from-orange-500 to-rose-500',
    divider: 'border-orange-100',
    card: 'bg-orange-50 ring-1 ring-orange-100',
    cardTitle: 'text-stone-900',
    number: 'text-orange-300',
    badge: 'bg-gradient-to-br from-orange-500 to-rose-500 text-white',
    bullet: 'border-rose-400',
    check: 'bg-rose-500 text-white',
    chip: 'bg-orange-50 text-orange-700 ring-1 ring-orange-200',
    arrow: 'text-orange-300',
    highlight: 'bg-gradient-to-br from-orange-500 to-rose-500 text-white',
    highlightLabel: 'text-orange-50',
    footer: 'text-stone-400',
  },
  ocean: {
    label: '오션',
    description: '청록 · 데이터·대시보드·모바일·여행',
    cover: {
      style: 'glow',
      bg: 'bg-gradient-to-br from-slate-950 via-cyan-900 to-teal-500 text-white',
      title: 'font-extrabold',
      sub: 'text-cyan-50',
      label: 'text-cyan-200',
      glowA: 'bg-cyan-300/25',
      glowB: 'bg-teal-300/20',
    },
    heading: 'font-sans font-bold tracking-tight',
    page: 'bg-slate-50 text-slate-900',
    muted: 'text-slate-600',
    kicker: 'text-cyan-600',
    bar: 'bg-gradient-to-r from-cyan-500 to-teal-400',
    divider: 'border-cyan-100',
    card: 'bg-white ring-1 ring-cyan-100',
    cardTitle: 'text-slate-900',
    number: 'text-cyan-300',
    badge: 'bg-cyan-600 text-white',
    bullet: 'border-cyan-500',
    check: 'bg-teal-500 text-white',
    chip: 'bg-cyan-50 text-cyan-800 ring-1 ring-cyan-200',
    arrow: 'text-cyan-300',
    highlight: 'bg-gradient-to-br from-cyan-600 to-teal-500 text-white',
    highlightLabel: 'text-cyan-50',
    footer: 'text-slate-400',
  },
  mono: {
    label: '모노',
    description: '흑백 고대비 · 미니멀 도구·디자인',
    cover: {
      style: 'mono',
      bg: 'bg-black text-white',
      title: 'font-black tracking-tighter',
      sub: 'text-neutral-300',
      label: 'text-neutral-500',
      glowA: '',
      glowB: '',
    },
    heading: 'font-sans font-black tracking-tighter',
    page: 'bg-white text-black',
    muted: 'text-neutral-600',
    kicker: 'text-black',
    bar: 'bg-black',
    divider: 'border-black',
    card: 'bg-neutral-100',
    cardTitle: 'text-black',
    number: 'text-neutral-300',
    badge: 'bg-black text-white',
    bullet: 'border-black',
    check: 'bg-black text-white',
    chip: 'border border-black bg-white text-black',
    arrow: 'text-black',
    highlight: 'bg-black text-white',
    highlightLabel: 'text-neutral-400',
    footer: 'text-neutral-400',
  },
  forest: {
    label: '포레스트',
    description: '초록 · 환경·건강·교육·게임·커뮤니티',
    cover: {
      style: 'glow',
      bg: 'bg-gradient-to-br from-emerald-950 via-green-800 to-lime-600 text-white',
      title: 'font-extrabold',
      sub: 'text-lime-50',
      label: 'text-lime-200',
      glowA: 'bg-lime-300/25',
      glowB: 'bg-emerald-300/20',
    },
    heading: 'font-sans font-bold tracking-tight',
    page: 'bg-[#f6f8f1] text-stone-900',
    muted: 'text-stone-600',
    kicker: 'text-green-700',
    bar: 'bg-gradient-to-r from-green-700 to-lime-500',
    divider: 'border-green-100',
    card: 'bg-white ring-1 ring-green-100',
    cardTitle: 'text-stone-900',
    number: 'text-green-300',
    badge: 'bg-green-700 text-white',
    bullet: 'border-green-600',
    check: 'bg-green-600 text-white',
    chip: 'bg-green-50 text-green-800 ring-1 ring-green-200',
    arrow: 'text-green-300',
    highlight: 'bg-gradient-to-br from-green-700 to-lime-600 text-white',
    highlightLabel: 'text-lime-50',
    footer: 'text-stone-400',
  },
}

export const THEME_NAMES = Object.keys(SLIDE_THEMES) as SlideThemeName[]
