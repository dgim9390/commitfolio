import type { Slide } from '../types'
import { ArrowRightIcon, CheckIcon } from './icons'

// 슬라이드 한 장. 화면 미리보기·썸네일·PDF 인쇄에 같이 쓴다.
// 글자 크기는 cqw(컨테이너 폭의 1%) 단위라서, 감싸는 요소에 container-type만 주면
// 썸네일이든 전체 화면이든 같은 비율로 보인다.

export interface DeckMeta {
  repoName: string
  owner: string
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
  if (slide.layout === 'cover') return <Cover slide={slide} meta={meta} />
  return (
    <div className="flex h-full w-full flex-col bg-white px-[5.5%] pt-[4.5%] pb-[3%] text-slate-900">
      <header>
        <p className="text-[1.05cqw] font-semibold tracking-[0.2em] text-indigo-600">{LAYOUT_LABEL[slide.layout]}</p>
        <h2 className="mt-[0.6%] text-[3cqw] leading-tight font-bold tracking-tight">{slide.title}</h2>
        <p className="mt-[0.8%] text-[1.75cqw] leading-snug text-slate-600">{slide.headline}</p>
        <div className="mt-[1.6%] h-[0.3cqw] w-[6%] rounded-full bg-gradient-to-r from-indigo-600 to-violet-500" />
      </header>
      {/* 내용이 적은 장은 본문을 세로 가운데에 (my-auto) */}
      <main className="mt-[2.6%] flex min-h-0 flex-1 flex-col overflow-hidden">
        <Body slide={slide} />
      </main>
      <footer className="flex items-center justify-between text-[1cqw] text-slate-400">
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

function Cover({ slide, meta }: { slide: Slide; meta: DeckMeta }) {
  return (
    <div className="relative flex h-full w-full flex-col justify-between overflow-hidden bg-gradient-to-br from-indigo-950 via-indigo-700 to-violet-600 p-[6%] text-white">
      {/* 장식용 빛 번짐 */}
      <div className="absolute -top-[20%] -right-[10%] h-[70%] w-[45%] rounded-full bg-violet-400/30 blur-3xl" />
      <div className="absolute -bottom-[30%] -left-[10%] h-[60%] w-[40%] rounded-full bg-indigo-400/20 blur-3xl" />
      <p className="relative text-[1.2cqw] font-semibold tracking-[0.25em] text-indigo-200">PROJECT · {meta.owner}</p>
      <div className="relative">
        <h1 className="text-[6.2cqw] leading-none font-extrabold tracking-tight">{slide.title}</h1>
        <p className="mt-[2.2%] max-w-[75%] text-[2.2cqw] leading-snug text-indigo-100">{slide.headline}</p>
      </div>
      {/* 분석 기간·커밋 수 같은 도구 쪽 정보는 발표에 필요 없어서 넣지 않는다. 아래 여백만 맞춘다 */}
      <div className="relative h-[1.2cqw]" />
    </div>
  )
}

function Body({ slide }: { slide: Slide }) {
  const points = slide.points

  if (slide.layout === 'agenda') {
    return (
      <ol className="my-auto grid grid-cols-2 gap-x-[5%] gap-y-[2.6cqw]">
        {points.map((p, i) => (
          <li key={i} className="flex gap-[1.4cqw] border-t border-slate-200 pt-[1.2cqw]">
            <span className="text-[2.8cqw] leading-none font-extrabold text-indigo-300">{String(i + 1).padStart(2, '0')}</span>
            <div>
              <p className="text-[1.85cqw] font-bold">{p.heading}</p>
              <p className="mt-[0.4cqw] text-[1.4cqw] leading-snug text-slate-500">{p.text}</p>
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
          <div key={i} className="rounded-[1cqw] bg-slate-50 p-[6%] ring-1 ring-slate-200">
            {slide.layout === 'problem' && (
              <span className="mb-[4%] flex h-[2.6cqw] w-[2.6cqw] items-center justify-center rounded-full bg-indigo-600 text-[1.2cqw] font-bold text-white">
                {i + 1}
              </span>
            )}
            <p className="text-[1.75cqw] font-bold text-slate-900">{p.heading}</p>
            <p className="mt-[3%] text-[1.45cqw] leading-snug text-slate-600">{p.text}</p>
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
            <span className="mt-[0.2%] flex h-[2.6cqw] w-[2.6cqw] shrink-0 items-center justify-center rounded-full bg-emerald-500 text-white">
              <CheckIcon className="h-[1.5cqw] w-[1.5cqw]" />
            </span>
            <p className="text-[1.9cqw] leading-snug">
              <b className="font-bold">{p.heading}</b> <span className="text-slate-600">{p.text}</span>
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
              <span className="rounded-[0.6cqw] bg-indigo-50 px-[1.2cqw] py-[0.6cqw] text-[1.2cqw] font-semibold whitespace-nowrap text-indigo-700 ring-1 ring-indigo-200">
                {step}
              </span>
              {i < slide.flow.length - 1 && <ArrowRightIcon className="h-[1.5cqw] w-[1.5cqw] text-indigo-300" />}
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
            <li key={i} className="border-l-[0.3cqw] border-indigo-500 pl-[2%]">
              <p className={`${roomy ? 'text-[1.9cqw]' : 'text-[1.55cqw]'} font-bold`}>{p.heading}</p>
              <p className={`mt-[0.5%] ${roomy ? 'text-[1.6cqw]' : 'text-[1.35cqw]'} leading-snug text-slate-600`}>{p.text}</p>
            </li>
          ))}
        </ul>
        {slide.highlights.length > 0 && (
          // 수치 카드는 남은 높이를 똑같이 나눠 가져서 개수와 상관없이 넘치지 않는다
          <div className="flex w-[26%] shrink-0 flex-col gap-[1cqw]">
            {slide.highlights.map((h, i) => (
              <div
                key={i}
                className="flex max-h-[48%] min-h-0 flex-1 flex-col justify-center rounded-[1cqw] bg-gradient-to-br from-indigo-600 to-violet-600 px-[1.6cqw] text-white"
              >
                <p className="text-[2.8cqw] leading-none font-extrabold">{h.value}</p>
                <p className="mt-[0.6cqw] text-[1.1cqw] leading-tight text-indigo-100">{h.label}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
