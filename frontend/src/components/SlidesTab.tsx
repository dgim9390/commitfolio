import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { slidesMarkdown, slideText } from '../format'
import type { AnalysisResult, Slide } from '../types'
import { CopyButton } from './CopyButton'
import { Evidence } from './Evidence'

/** 16:9 슬라이드 한 장. 화면 미리보기와 PDF 인쇄에 같이 쓴다 */
function SlideCard({ slide, index, total, repoName, cover }: { slide: Slide; index: number; total: number; repoName: string; cover: boolean }) {
  return (
    <div className="flex h-full w-full flex-col bg-white p-[6%] text-zinc-900">
      {cover ? (
        <div className="flex flex-1 flex-col justify-center">
          {/* 제목이 레포 이름과 같으면 위의 작은 이름표는 중복이라 숨긴다 */}
          {slide.title.toLowerCase() !== repoName.toLowerCase() && (
            <p className="text-[1.6cqw] font-medium tracking-wide text-indigo-600">{repoName}</p>
          )}
          <h2 className="mt-[1.5%] text-[5cqw] font-bold leading-tight">{slide.title}</h2>
          {slide.bullets.map((b, i) => (
            <p key={i} className="mt-[2%] text-[2.2cqw] text-zinc-600">
              {b.text}
            </p>
          ))}
        </div>
      ) : (
        <>
          <h2 className="border-b-2 border-indigo-600 pb-[1.5%] text-[3.2cqw] font-bold">{slide.title}</h2>
          <ul className="mt-[3%] flex-1 space-y-[2%]">
            {slide.bullets.map((b, i) => (
              <li key={i} className="flex gap-[1.5%] text-[2.1cqw] leading-snug">
                <span className="text-indigo-600">•</span>
                <span>{b.text}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="text-right text-[1.2cqw] text-zinc-400">
        {index + 1} / {total}
      </p>
    </div>
  )
}

export function SlidesTab({ result }: { result: AnalysisResult }) {
  const slides = result.outputs.slides
  const [current, setCurrent] = useState(0)
  const [showNotes, setShowNotes] = useState(true)
  const slide = slides[current]

  // ← → 키로 넘기기 (입력창에 포커스가 있을 때는 무시)
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === 'ArrowRight') setCurrent((c) => Math.min(c + 1, slides.length - 1))
      if (e.key === 'ArrowLeft') setCurrent((c) => Math.max(c - 1, 0))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [slides.length])

  if (!slide) return <p className="text-sm text-zinc-500">만들어진 슬라이드가 없습니다.</p>

  const card = (s: Slide, i: number) => (
    <SlideCard slide={s} index={i} total={slides.length} repoName={result.repo.name} cover={i === 0} />
  )

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <CopyButton text={() => slideText(slide)} label="이 장 복사" />
        <CopyButton text={() => slidesMarkdown(result)} label="전체 복사" />
        <button
          onClick={() => window.print()}
          className="rounded-md bg-indigo-600 px-3 py-1 text-xs font-semibold text-white hover:bg-indigo-500"
        >
          PDF로 저장
        </button>
      </div>

      {/* cqw 단위(컨테이너 폭 기준)를 쓰려고 container-type을 준다 → 화면 크기와 상관없이 같은 비율 */}
      <div className="aspect-video w-full overflow-hidden rounded-xl border border-zinc-200 shadow-sm [container-type:inline-size] dark:border-zinc-700">
        {card(slide, current)}
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={() => setCurrent((c) => Math.max(c - 1, 0))}
          disabled={current === 0}
          className="rounded-md px-3 py-1.5 text-sm hover:bg-zinc-200 disabled:opacity-30 dark:hover:bg-zinc-800"
        >
          ← 이전
        </button>
        <div className="flex gap-1.5">
          {slides.map((s, i) => (
            <button
              key={i}
              onClick={() => setCurrent(i)}
              aria-label={`${i + 1}장: ${s.title}`}
              className={`h-2 rounded-full transition-all ${i === current ? 'w-6 bg-indigo-600' : 'w-2 bg-zinc-300 dark:bg-zinc-700'}`}
            />
          ))}
        </div>
        <button
          onClick={() => setCurrent((c) => Math.min(c + 1, slides.length - 1))}
          disabled={current === slides.length - 1}
          className="rounded-md px-3 py-1.5 text-sm hover:bg-zinc-200 disabled:opacity-30 dark:hover:bg-zinc-800"
        >
          다음 →
        </button>
      </div>

      <div className="rounded-lg border border-zinc-200 p-4 text-sm dark:border-zinc-800">
        <button onClick={() => setShowNotes((v) => !v)} className="text-xs font-semibold text-zinc-500">
          {showNotes ? '▾' : '▸'} 발표자 메모 · 근거
        </button>
        {showNotes && (
          <div className="mt-2 space-y-3">
            <p className="leading-relaxed text-zinc-700 dark:text-zinc-300">{slide.notes}</p>
            {slide.bullets.map((b, i) => (
              <div key={i}>
                <p className="text-xs text-zinc-500">{b.text}</p>
                <Evidence statement={b} result={result} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 인쇄용: 모든 장을 페이지마다 하나씩. 앱 화면(no-print) 바깥에 둬야 인쇄 때 보인다 */}
      {createPortal(
        <div className="print-only">
          {slides.map((s, i) => (
            <div key={i} className="print-slide [container-type:inline-size]">
              {card(s, i)}
            </div>
          ))}
        </div>,
        document.body,
      )}
    </div>
  )
}
