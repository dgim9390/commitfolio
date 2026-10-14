import { SLIDE_THEMES, type SlideTheme } from '../slideThemes'
import type { Slide, SlideThemeName } from '../types'
import { ArrowRightIcon, CheckIcon } from './icons'

// 슬라이드 한 장. 화면 미리보기·썸네일·PDF 인쇄에 같이 쓴다.
// 글자 크기는 cqw(컨테이너 폭의 1%) 단위라서, 감싸는 요소에 container-type만 주면
// 썸네일이든 전체 화면이든 같은 비율로 보인다.
// 색·글꼴·장식은 테마(slideThemes.ts)에서 가져오고, 여기서는 배치만 정한다.

export interface DeckMeta {
  repoName: string
  owner: string
  theme: SlideThemeName
}

const LAYOUT_LABEL: Record<Slide['layout'], string> = {
  cover: '',
  agenda: 'AGENDA',
  problem: 'PROBLEM',
  feature: 'FEATURE',
  architecture: 'ARCHITECTURE',
  tech: 'TECH STACK',
  summary: 'SUMMARY',
}

const COLS = ['grid-cols-1', 'grid-cols-1', 'grid-cols-2', 'grid-cols-3', 'grid-cols-2']

export function SlideCard({ slide, index, total, meta }: { slide: Slide; index: number; total: number; meta: DeckMeta }) {
  const t = SLIDE_THEMES[meta.theme] ?? SLIDE_THEMES.aurora
  if (slide.layout === 'cover') return <Cover slide={slide} meta={meta} t={t} />
  return (
    <div className={`flex h-full w-full flex-col px-[5.5%] pt-[4.5%] pb-[3%] ${t.page}`}>
      <header>
        <p className={`text-[1.05cqw] font-semibold tracking-[0.2em] ${t.kicker}`}>{LAYOUT_LABEL[slide.layout]}</p>
        <h2 className={`mt-[0.6%] text-[3cqw] leading-tight ${t.heading}`}>{slide.title}</h2>
        <p className={`mt-[0.8%] text-[1.75cqw] leading-snug ${t.muted}`}>{slide.headline}</p>
        <div className={`mt-[1.6%] h-[0.3cqw] w-[6%] rounded-full ${t.bar}`} />
      </header>
      {/* 내용이 적은 장은 본문을 세로 가운데에 (my-auto) */}
      <main className="mt-[2.6%] flex min-h-0 flex-1 flex-col overflow-hidden">
        <Body slide={slide} t={t} />
      </main>
      <footer className={`flex items-center justify-between text-[1cqw] ${t.footer}`}>
        <span>
          {meta.owner}/{meta.repoName}
        </span>
        <span>
          {index + 1} / {total}
        </span>
      </footer>
    </div>
  )
}

function Cover({ slide, meta, t }: { slide: Slide; meta: DeckMeta; t: SlideTheme }) {
  const c = t.cover
  const title = <h1 className={`text-[6.2cqw] leading-none ${c.title}`}>{slide.title}</h1>
  const sub = <p className={`mt-[2.2%] max-w-[75%] text-[2.2cqw] leading-snug ${c.sub}`}>{slide.headline}</p>

  // 터미널: 창 테두리 + 명령어 줄 + 깜빡이는 커서
  if (c.style === 'terminal') {
    return (
      <div className={`flex h-full w-full flex-col p-[4%] ${c.bg}`}>
        <div className="flex flex-1 flex-col overflow-hidden rounded-[1cqw] ring-1 ring-white/10">
          <div className="flex items-center gap-[0.7cqw] border-b border-white/10 bg-white/[0.03] px-[1.6cqw] py-[1cqw]">
            {['bg-red-400/80', 'bg-amber-300/80', 'bg-emerald-400/80'].map((dot) => (
              <span key={dot} className={`h-[1cqw] w-[1cqw] rounded-full ${dot}`} />
            ))}
            <span className="ml-[1cqw] font-mono text-[1.1cqw] text-slate-500">
              ~/{meta.owner}/{meta.repoName}
            </span>
          </div>
          <div className="flex flex-1 flex-col justify-center px-[5%]">
            <p className={`text-[1.4cqw] ${c.label}`}>$ cat README.md</p>
            <div className="mt-[2%] flex items-end gap-[1cqw]">
              {title}
              <span className="mb-[0.4cqw] h-[4.6cqw] w-[2cqw] animate-pulse bg-emerald-300" />
            </div>
            <p className="mt-[2.2%] max-w-[80%] font-mono text-[1.9cqw] leading-snug text-slate-400"># {slide.headline}</p>
          </div>
        </div>
      </div>
    )
  }

  // 페이퍼: 보고서 표지처럼 굵은 가로줄과 명조체
  if (c.style === 'paper') {
    return (
      <div className={`flex h-full w-full flex-col justify-between p-[6%] ${c.bg}`}>
        <div className="flex items-baseline justify-between border-b-[0.25cqw] border-stone-900 pb-[1.2%]">
          <p className={`text-[1.5cqw] ${c.label}`}>Project Report</p>
          <p className="font-serif text-[1.2cqw] text-stone-500">
            {meta.owner}/{meta.repoName}
          </p>
        </div>
        <div>
          {title}
          {sub}
        </div>
        <div className="border-t border-stone-400" />
      </div>
    )
  }

  // 모노: 검은 바탕에 아주 큰 제목과 흰 막대
  if (c.style === 'mono') {
    return (
      <div className={`flex h-full w-full flex-col justify-between p-[6%] ${c.bg}`}>
        <p className={`text-[1.2cqw] font-semibold tracking-[0.3em] ${c.label}`}>{meta.owner.toUpperCase()}</p>
        <div>
          <div className="mb-[3%] h-[0.8cqw] w-[12%] bg-white" />
          <h1 className={`text-[8cqw] leading-[0.95] ${c.title}`}>{slide.title}</h1>
          {sub}
        </div>
        <div className="h-[1.2cqw]" />
      </div>
    )
  }

  // 빛 번짐 (오로라·선셋·오션·포레스트)
  return (
    <div className={`relative flex h-full w-full flex-col justify-between overflow-hidden p-[6%] ${c.bg}`}>
      <div className={`absolute -top-[20%] -right-[10%] h-[70%] w-[45%] rounded-full blur-3xl ${c.glowA}`} />
      <div className={`absolute -bottom-[30%] -left-[10%] h-[60%] w-[40%] rounded-full blur-3xl ${c.glowB}`} />
      <p className={`relative text-[1.2cqw] font-semibold tracking-[0.25em] ${c.label}`}>PROJECT · {meta.owner}</p>
      <div className="relative">
        {title}
        {sub}
      </div>
      {/* 분석 기간·커밋 수 같은 도구 쪽 정보는 발표에 필요 없어서 넣지 않는다. 아래 여백만 맞춘다 */}
      <div className="relative h-[1.2cqw]" />
    </div>
  )
}

function Body({ slide, t }: { slide: Slide; t: SlideTheme }) {
  const points = slide.points

  if (slide.layout === 'agenda') {
    return (
      <ol className="my-auto grid grid-cols-2 gap-x-[5%] gap-y-[2.6cqw]">
        {points.map((p, i) => (
          <li key={i} className={`flex gap-[1.4cqw] border-t pt-[1.2cqw] ${t.divider}`}>
            <span className={`text-[2.8cqw] leading-none font-extrabold ${t.number}`}>{String(i + 1).padStart(2, '0')}</span>
            <div>
              <p className={`text-[1.85cqw] ${t.heading}`}>{p.heading}</p>
              <p className={`mt-[0.4cqw] text-[1.4cqw] leading-snug ${t.muted}`}>{p.text}</p>
            </div>
          </li>
        ))}
      </ol>
    )
  }

  if (slide.layout === 'problem' || slide.layout === 'tech') {
    return (
      // Tailwind는 코드에 그대로 적힌 클래스만 만들어 주므로 grid-cols-${n} 대신 표로 고른다
      <div className={`my-auto grid content-start gap-[2%] ${COLS[Math.min(points.length, 4)]}`}>
        {points.map((p, i) => (
          <div key={i} className={`rounded-[1cqw] p-[6%] ${t.card}`}>
            {slide.layout === 'problem' && (
              <span className={`mb-[4%] flex h-[2.6cqw] w-[2.6cqw] items-center justify-center rounded-full text-[1.2cqw] font-bold ${t.badge}`}>
                {i + 1}
              </span>
            )}
            <p className={`text-[1.75cqw] font-bold ${t.cardTitle}`}>{p.heading}</p>
            <p className={`mt-[3%] text-[1.45cqw] leading-snug ${t.muted}`}>{p.text}</p>
          </div>
        ))}
      </div>
    )
  }

  if (slide.layout === 'summary') {
    return (
      <ul className="my-auto space-y-[3.5%]">
        {points.map((p, i) => (
          <li key={i} className="flex items-start gap-[1.6%]">
            <span className={`mt-[0.2%] flex h-[2.6cqw] w-[2.6cqw] shrink-0 items-center justify-center rounded-full ${t.check}`}>
              <CheckIcon className="h-[1.5cqw] w-[1.5cqw]" />
            </span>
            <p className="text-[1.9cqw] leading-snug">
              <b className="font-bold">{p.heading}</b> <span className={t.muted}>{p.text}</span>
            </p>
          </li>
        ))}
      </ul>
    )
  }

  // feature / architecture
  const roomy = !slide.flow.length && !slide.highlights.length
  return (
    <div className={`flex flex-col gap-[3%] ${roomy ? 'my-auto' : 'h-full'}`}>
      {slide.flow.length > 0 && (
        <div className="flex flex-wrap items-center gap-[1%]">
          {slide.flow.map((step, i) => (
            <div key={i} className="flex items-center gap-[1%]">
              <span className={`rounded-[0.6cqw] px-[1.2cqw] py-[0.6cqw] text-[1.2cqw] font-semibold whitespace-nowrap ${t.chip}`}>{step}</span>
              {i < slide.flow.length - 1 && <ArrowRightIcon className={`h-[1.5cqw] w-[1.5cqw] ${t.arrow}`} />}
            </div>
          ))}
        </div>
      )}
      <div className="flex min-h-0 flex-1 gap-[3%]">
        <ul
          className={`min-w-0 flex-1 ${
            slide.flow.length ? 'grid grid-cols-2 content-start items-start gap-x-[3%] gap-y-[6%]' : roomy ? 'space-y-[4%]' : 'space-y-[2.4%]'
          }`}
        >
          {points.map((p, i) => (
            <li key={i} className={`border-l-[0.3cqw] pl-[2%] ${t.bullet}`}>
              <p className={`${roomy ? 'text-[1.9cqw]' : 'text-[1.55cqw]'} font-bold`}>{p.heading}</p>
              <p className={`mt-[0.5%] ${roomy ? 'text-[1.6cqw]' : 'text-[1.35cqw]'} leading-snug ${t.muted}`}>{p.text}</p>
            </li>
          ))}
        </ul>
        {slide.highlights.length > 0 && (
          // 수치 카드는 남은 높이를 똑같이 나눠 가져서 개수와 상관없이 넘치지 않는다
          <div className="flex w-[26%] shrink-0 flex-col gap-[1cqw]">
            {slide.highlights.map((h, i) => (
              <div key={i} className={`flex max-h-[48%] min-h-0 flex-1 flex-col justify-center rounded-[1cqw] px-[1.6cqw] ${t.highlight}`}>
                <p className="text-[2.8cqw] leading-none font-extrabold">{h.value}</p>
                <p className={`mt-[0.6cqw] text-[1.1cqw] leading-tight ${t.highlightLabel}`}>{h.label}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
