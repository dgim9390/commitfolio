import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { slidesMarkdown, slideText } from '../format'
import { projectMeta } from '../meta'
import type { AnalysisResult } from '../types'
import { CopyButton } from './CopyButton'
import { Evidence } from './Evidence'
import { DownloadIcon, ExpandIcon } from './icons'
import type { Edit } from './ResultView'
import { SlideCard, type DeckMeta } from './SlideCard'
import { SlideEditor } from './SlideEditor'

export function SlidesTab({ result, edit }: { result: AnalysisResult; edit: Edit | null }) {
  const slides = result.outputs.slides
  // 주소창 ?slide=4 로 특정 장을 바로 열 수 있다 (링크 공유용)
  const [current, setCurrentState] = useState(() => {
    const n = Number(new URLSearchParams(window.location.search).get('slide'))
    return n >= 1 && n <= slides.length ? n - 1 : 0
  })

  function setCurrent(update: (c: number) => number) {
    setCurrentState((c) => {
      const next = update(c)
      const params = new URLSearchParams(window.location.search)
      params.set('slide', String(next + 1))
      window.history.replaceState(null, '', `?${params}`)
      return next
    })
  }
  const stage = useRef<HTMLDivElement>(null)
  // 편집 중에 장을 지우면 current가 범위를 넘을 수 있어 마지막 장으로 맞춘다
  const slide = slides[Math.min(current, slides.length - 1)]
  const m = projectMeta(result)
  const meta: DeckMeta = { repoName: result.repo.name, owner: result.repo.owner, period: m.period, commits: m.commits, works: m.works }

  // ← → (와 스페이스) 키로 넘기기. 입력창에 포커스가 있을 때는 무시
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const t = e.target
      if (t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || t instanceof HTMLSelectElement) return
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault()
        setCurrent((c) => Math.min(c + 1, slides.length - 1))
      }
      if (e.key === 'ArrowLeft') setCurrent((c) => Math.max(c - 1, 0))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [slides.length])

  if (!slide) return <p className="text-sm text-slate-500">만들어진 슬라이드가 없습니다.</p>

  const btn =
    'inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-500">
          <b className="text-slate-800 dark:text-slate-200">{slides.length}장</b> · ← → 키로 넘기기
        </p>
        <div className="flex flex-wrap gap-2">
          <CopyButton text={() => slideText(slide)} label="이 장 복사" />
          <CopyButton text={() => slidesMarkdown(result)} label="전체 복사" />
          <button className={btn} onClick={() => stage.current?.requestFullscreen?.()}>
            <ExpandIcon /> 발표 모드
          </button>
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-indigo-500"
          >
            <DownloadIcon /> PDF로 저장
          </button>
        </div>
      </div>

      {/* 발표 모드(전체 화면)에서도 16:9를 유지하도록 가운데 정렬 */}
      <div ref={stage} className="flex items-center justify-center bg-slate-900 [&:not(:fullscreen)]:bg-transparent">
        <div className="aspect-video w-full overflow-hidden rounded-xl shadow-xl ring-1 shadow-indigo-900/10 ring-slate-200 [container-type:inline-size] dark:ring-slate-700 [:fullscreen_&]:max-h-screen [:fullscreen_&]:w-auto [:fullscreen_&]:rounded-none">
          <SlideCard slide={slide} index={current} total={slides.length} meta={meta} />
        </div>
      </div>

      {/* 썸네일: 같은 SlideCard를 작은 상자에 넣으면 cqw 덕분에 그대로 축소된다 */}
      <div className="flex gap-2 overflow-x-auto p-1 pb-2">
        {slides.map((s, i) => (
          <button
            key={i}
            onClick={() => setCurrent(() => i)}
            aria-label={`${i + 1}장: ${s.title}`}
            className={`aspect-video w-32 shrink-0 overflow-hidden rounded-md transition [container-type:inline-size] ${
              i === current ? 'ring-2 ring-indigo-500 ring-offset-2 dark:ring-offset-slate-950' : 'opacity-60 ring-1 ring-slate-200 hover:opacity-100 dark:ring-slate-700'
            }`}
          >
            <div className="pointer-events-none h-full w-full">
              <SlideCard slide={s} index={i} total={slides.length} meta={meta} />
            </div>
          </button>
        ))}
      </div>

      {edit ? (
        <SlideEditor slide={slide} index={Math.min(current, slides.length - 1)} total={slides.length} edit={edit} onMove={(to) => setCurrent(() => to)} />
      ) : (
      <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-800 dark:bg-slate-900/40">
        <p className="text-xs font-semibold tracking-wide text-slate-500">발표자 메모</p>
        <p className="mt-1.5 text-sm leading-relaxed text-slate-700 dark:text-slate-300">{slide.notes}</p>
        {slide.points.length > 0 && (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer text-xs font-semibold text-slate-500">이 장의 근거 커밋</summary>
            <div className="mt-2 space-y-2">
              {slide.points.map((p, i) => (
                <div key={i}>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    <b>{p.heading}</b> {p.text}
                  </p>
                  <Evidence statement={p} result={result} />
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
      )}

      {/* 인쇄용: 모든 장을 페이지마다 하나씩. 앱 화면(no-print) 바깥에 둬야 인쇄 때 보인다 */}
      {createPortal(
        <div className="print-only">
          {slides.map((s, i) => (
            <div key={i} className="print-slide [container-type:inline-size]">
              <SlideCard slide={s} index={i} total={slides.length} meta={meta} />
            </div>
          ))}
        </div>,
        document.body,
      )}
    </div>
  )
}
