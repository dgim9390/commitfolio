import { useState } from 'react'
import { designOf } from '../design'
import { editStatement, newStatement } from '../edit'
import { portfolioMarkdown } from '../format'
import type { AnalysisResult, Contribution, Statement } from '../types'
import { CopyButton } from './CopyButton'
import { DesignPicker } from './DesignPicker'
import { AddButton, EditList, EditText, RemoveButton } from './Editable'
import { Evidence } from './Evidence'
import { PortfolioView } from './PortfolioView'
import type { Edit } from './ResultView'

/** edit가 있으면 편집 모드: 글자 대신 입력 칸을 보여준다 */
export function PortfolioTab({ result, edit }: { result: AnalysisResult; edit: Edit | null }) {
  const p = result.outputs.portfolio
  const [withLinks, setWithLinks] = useState(true)

  // 보기: 디자인이 적용된 포트폴리오 페이지
  if (!edit) {
    return (
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-end gap-3">
          <label className="flex items-center gap-1.5 text-xs text-slate-500">
            <input type="checkbox" className="accent-indigo-600" checked={withLinks} onChange={(e) => setWithLinks(e.target.checked)} />
            복사할 때 근거 링크 포함
          </label>
          <CopyButton text={() => portfolioMarkdown(result, withLinks)} label="전체 복사 (마크다운)" primary />
        </div>
        <PortfolioView result={result} withLinks={withLinks} />
      </div>
    )
  }

  // 편집: 입력 칸이 잘 보이도록 디자인 없이 중립적인 화면으로 고친다
  return (
    <div className="space-y-10">
      <DesignPicker design={designOf(result.outputs)} edit={edit} />

      {/* 개요: 한 줄 소개를 크게, 설명은 읽기 좋은 폭으로 */}
      <section>
        <p className="text-xs font-semibold tracking-[0.2em] text-indigo-600 dark:text-indigo-400">OVERVIEW</p>
        <div className="mt-2 max-w-3xl space-y-2">
          <EditText label="한 줄 소개" value={p.tagline} onChange={(v) => edit((d) => void (d.portfolio.tagline = v))} className="text-2xl font-bold" />
          <EditText
            label="프로젝트 개요"
            multiline
            value={p.overview}
            onChange={(v) => edit((d) => void (d.portfolio.overview = v))}
            className="text-[15px] leading-7"
          />
        </div>
      </section>

      <section>
        <SectionTitle label="KEY CONTRIBUTIONS" title="주요 기여" count={p.contributions.length} />
        <ol className="mt-4 space-y-4">
          {p.contributions.map((c, i) => (
            <ContributionCard key={i} c={c} index={i} result={result} edit={edit} />
          ))}
        </ol>
        <div className="mt-3">
          <AddButton
            onClick={() =>
              edit((d) => void d.portfolio.contributions.push({ title: '', summary: newStatement(), points: [], technologies: [] }))
            }
          >
            기여 추가
          </AddButton>
        </div>
      </section>

      <section>
        <SectionTitle label="TECH STACK" title="기술 스택" />
        <dl className="mt-4 divide-y divide-slate-100 rounded-2xl border border-slate-200 dark:divide-slate-800 dark:border-slate-800">
          {p.tech_stack.map((g, gi) => (
            <div key={gi} className="grid gap-2 px-5 py-3.5 sm:grid-cols-[160px_1fr] sm:items-center">
              <EditText
                label="기술 분야"
                value={g.category}
                onChange={(v) => edit((d) => void (d.portfolio.tech_stack[gi].category = v))}
                className="text-sm font-semibold"
              />
              <div className="flex items-center gap-2">
                <EditList
                  label={`${g.category} 기술`}
                  items={g.items}
                  onChange={(v) => edit((d) => void (d.portfolio.tech_stack[gi].items = v))}
                />
                <RemoveButton label="이 분야 삭제" onClick={() => edit((d) => void d.portfolio.tech_stack.splice(gi, 1))} />
              </div>
            </div>
          ))}
        </dl>
        <div className="mt-3">
          <AddButton onClick={() => edit((d) => void d.portfolio.tech_stack.push({ category: '', items: [] }))}>분야 추가</AddButton>
        </div>
      </section>
    </div>
  )
}

function SectionTitle({ label, title, count }: { label: string; title: string; count?: number }) {
  return (
    <div>
      <p className="text-xs font-semibold tracking-[0.2em] text-indigo-600 dark:text-indigo-400">{label}</p>
      <h3 className="mt-1 text-lg font-bold">
        {title} {count !== undefined && <span className="text-slate-400">{count}</span>}
      </h3>
    </div>
  )
}

/** 라벨 + 입력 칸 한 줄. 보기 화면(PortfolioView)과 같은 "배경 → 한 일 → 결과" 순서로 둔다 */
function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[3.75rem_1fr] sm:gap-3">
      <p className="pt-1.5 text-xs font-semibold tracking-wide text-indigo-600 dark:text-indigo-400">{label}</p>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function ContributionCard({ c, index, result, edit }: { c: Contribution; index: number; result: AnalysisResult; edit: Edit }) {
  // 이 기여 하나를 고치는 단축 함수
  const editC = (change: (c: Contribution) => void) => edit((d) => change(d.portfolio.contributions[index]))
  // 배경·결과는 예전 결과에 없을 수 있어서, 고치는 순간에 만든다
  const text = (s?: Statement | null) => s?.text ?? ''

  return (
    <li className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6 dark:border-slate-800 dark:bg-slate-900/40">
      <div className="flex items-start gap-4">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-sm font-bold text-white">
          {String(index + 1).padStart(2, '0')}
        </span>
        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex items-start justify-between gap-3">
            <EditText
              label="기여 제목"
              value={c.title}
              placeholder="기여 제목"
              onChange={(v) => editC((x) => void (x.title = v))}
              className="text-lg font-bold"
            />
            <RemoveButton label="이 기여 삭제" onClick={() => edit((d) => void d.portfolio.contributions.splice(index, 1))} />
          </div>

          <Row label="배경">
            <EditText
              label="기여 배경"
              multiline
              value={text(c.background)}
              placeholder="어떤 문제나 필요가 있었는지 한 문장"
              onChange={(v) => editC((x) => void (x.background = editStatement(x.background ?? newStatement(), v)))}
              className="text-[15px] leading-7"
            />
            {c.background && <Evidence statement={c.background} result={result} />}
          </Row>

          <Row label="한 일">
            <EditText
              label="기여 요약"
              multiline
              value={c.summary.text}
              placeholder="무엇을 어떤 기술로 만들었는지 한 문장"
              onChange={(v) => editC((x) => void (x.summary = editStatement(x.summary, v)))}
              className="leading-7"
            />
            <Evidence statement={c.summary} result={result} />

            <ul className="mt-3 space-y-2.5">
              {c.points.map((p, i) => (
                <li key={i}>
                  <div className="flex items-start gap-1">
                    <EditText
                      label={`구현 포인트 ${i + 1}`}
                      multiline
                      value={p.text}
                      onChange={(v) => editC((x) => void (x.points[i] = editStatement(x.points[i], v)))}
                      className="text-[15px] leading-6"
                    />
                    <RemoveButton label="이 포인트 삭제" onClick={() => editC((x) => void x.points.splice(i, 1))} />
                  </div>
                  <Evidence statement={p} result={result} />
                </li>
              ))}
              <li>
                <AddButton onClick={() => editC((x) => void x.points.push(newStatement()))}>포인트 추가</AddButton>
              </li>
            </ul>
          </Row>

          <Row label="결과">
            <EditText
              label="기여 결과"
              multiline
              value={text(c.outcome)}
              placeholder="근거로 확인되는 결과 (없으면 비워 둡니다)"
              onChange={(v) => editC((x) => void (x.outcome = editStatement(x.outcome ?? newStatement(), v)))}
              className="leading-7"
            />
            {c.outcome && <Evidence statement={c.outcome} result={result} />}
          </Row>

          <Row label="기술">
            <EditList label="기술 태그" items={c.technologies} onChange={(v) => editC((x) => void (x.technologies = v))} />
          </Row>
        </div>
      </div>
    </li>
  )
}
