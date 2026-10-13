import { editStatement, newStatement } from '../edit'
import type { Slide } from '../types'
import { AddButton, EditList, EditText, RemoveButton } from './Editable'
import type { Edit } from './ResultView'

const LAYOUTS: { value: Slide['layout']; label: string }[] = [
  { value: 'cover', label: '표지' },
  { value: 'agenda', label: '목차' },
  { value: 'problem', label: '문제 정의' },
  { value: 'feature', label: '기능' },
  { value: 'architecture', label: '구조(흐름도)' },
  { value: 'tech', label: '기술 스택' },
  { value: 'summary', label: '정리' },
]

/** 현재 장을 고치는 패널. 고친 내용은 위의 슬라이드 미리보기에 바로 반영된다 */
export function SlideEditor({
  slide,
  index,
  total,
  edit,
  onMove,
}: {
  slide: Slide
  index: number
  total: number
  edit: Edit
  onMove: (to: number) => void
}) {
  // 이 장 하나를 고치는 단축 함수
  const editS = (change: (s: Slide) => void) => edit((d) => change(d.slides[index]))
  const label = 'mb-1 block text-[11px] font-semibold text-slate-500'

  function move(to: number) {
    edit((d) => {
      const [s] = d.slides.splice(index, 1)
      d.slides.splice(to, 0, s)
    })
    onMove(to)
  }

  return (
    <div className="space-y-4 rounded-xl border border-indigo-200 bg-indigo-50/30 p-4 dark:border-indigo-900 dark:bg-indigo-950/10">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold text-indigo-700 dark:text-indigo-300">{index + 1}장 고치기</p>
        <div className="flex items-center gap-1 text-xs">
          <button type="button" disabled={index === 0} onClick={() => move(index - 1)} className="rounded-md px-2 py-1 hover:bg-white disabled:opacity-30 dark:hover:bg-slate-800">
            ← 앞으로
          </button>
          <button type="button" disabled={index === total - 1} onClick={() => move(index + 1)} className="rounded-md px-2 py-1 hover:bg-white disabled:opacity-30 dark:hover:bg-slate-800">
            뒤로 →
          </button>
          <RemoveButton
            label="이 장 삭제"
            onClick={() => {
              if (!window.confirm(`${index + 1}장 '${slide.title}'을 삭제할까요?`)) return
              edit((d) => void d.slides.splice(index, 1))
              onMove(Math.max(0, Math.min(index, total - 2)))
            }}
          />
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-[1fr_160px]">
        <label>
          <span className={label}>제목</span>
          <EditText label="슬라이드 제목" value={slide.title} onChange={(v) => editS((s) => void (s.title = v))} className="text-sm font-bold" />
        </label>
        <label>
          <span className={label}>레이아웃</span>
          <select
            value={slide.layout}
            onChange={(e) => editS((s) => void (s.layout = e.target.value as Slide['layout']))}
            className="w-full rounded-lg border border-dashed border-indigo-300 bg-white px-2 py-1.5 text-sm dark:border-indigo-800 dark:bg-slate-900"
          >
            {LAYOUTS.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="block">
        <span className={label}>핵심 메시지 (제목 아래 한 문장)</span>
        <EditText label="핵심 메시지" multiline value={slide.headline} onChange={(v) => editS((s) => void (s.headline = v))} className="text-sm" />
      </label>

      <div>
        <span className={label}>항목 (굵은 키워드 + 설명)</span>
        <div className="space-y-2">
          {slide.points.map((p, i) => (
            <div key={i} className="grid gap-1.5 sm:grid-cols-[150px_1fr_auto] sm:items-start">
              <EditText label={`항목 ${i + 1} 키워드`} value={p.heading} placeholder="키워드" onChange={(v) => editS((s) => void (s.points[i] = { ...s.points[i], heading: v, edited: true }))} className="text-sm font-semibold" />
              <EditText label={`항목 ${i + 1} 설명`} multiline value={p.text} placeholder="한 문장 설명" onChange={(v) => editS((s) => void (s.points[i] = editStatement(s.points[i], v)))} className="text-sm" />
              <RemoveButton label="이 항목 삭제" onClick={() => editS((s) => void s.points.splice(i, 1))} />
            </div>
          ))}
          <AddButton onClick={() => editS((s) => void s.points.push({ ...newStatement(), heading: '' }))}>항목 추가</AddButton>
        </div>
      </div>

      {(slide.layout === 'feature' || slide.layout === 'architecture') && (
        <div>
          <span className={label}>숫자 카드 (예: 19종 / 지원 제품 수)</span>
          <div className="space-y-2">
            {slide.highlights.map((h, i) => (
              <div key={i} className="grid grid-cols-[110px_1fr_auto] items-start gap-1.5">
                <EditText label={`숫자 카드 ${i + 1} 값`} value={h.value} onChange={(v) => editS((s) => void (s.highlights[i].value = v))} className="text-sm font-bold" />
                <EditText label={`숫자 카드 ${i + 1} 설명`} value={h.label} onChange={(v) => editS((s) => void (s.highlights[i].label = v))} className="text-sm" />
                <RemoveButton label="이 숫자 카드 삭제" onClick={() => editS((s) => void s.highlights.splice(i, 1))} />
              </div>
            ))}
            {slide.highlights.length < 3 && (
              <AddButton onClick={() => editS((s) => void s.highlights.push({ value: '', label: '', evidence: [], from_readme: false }))}>숫자 카드 추가</AddButton>
            )}
          </div>
        </div>
      )}

      {slide.layout === 'architecture' && (
        <label className="block">
          <span className={label}>흐름도 단계</span>
          <EditList label="흐름도 단계" items={slide.flow} placeholder="쉼표로 구분 (예: 입력, 처리, 저장)" onChange={(v) => editS((s) => void (s.flow = v))} />
        </label>
      )}

      <label className="block">
        <span className={label}>발표자 메모</span>
        <EditText label="발표자 메모" multiline value={slide.notes} onChange={(v) => editS((s) => void (s.notes = v))} className="text-sm leading-relaxed" />
      </label>
    </div>
  )
}
