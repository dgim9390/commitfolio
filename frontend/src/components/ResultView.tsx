import { useEffect, useState } from 'react'
import { resetOutputs, saveOutputs } from '../api'
import { cleanOutputs } from '../edit'
import { projectMeta } from '../meta'
import type { AnalysisResult, Job, Outputs } from '../types'
import { GitHubIcon } from './icons'
import { NotesTab } from './NotesTab'
import { PortfolioTab } from './PortfolioTab'
import { SlidesTab } from './SlidesTab'

const TABS = [
  { key: 'portfolio', label: '포트폴리오' },
  { key: 'slides', label: '발표 자료' },
  { key: 'notes', label: '근거·검증' },
] as const
type TabKey = (typeof TABS)[number]['key']

const LANG_COLORS = ['bg-indigo-500', 'bg-violet-400', 'bg-sky-400', 'bg-slate-300']

export type Edit = (change: (draft: Outputs) => void) => void

export function ResultView({ job, onJobChange }: { job: Job; onJobChange: (job: Job) => void }) {
  const original = job.result as AnalysisResult
  // 화면에 보이는 결과: 편집 중이면 초안, 저장된 수정본이 있으면 그것, 없으면 AI 원본
  const [draft, setDraft] = useState<Outputs | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const editing = draft !== null
  const outputs = draft ?? job.edited_outputs ?? original.outputs
  const result: AnalysisResult = { ...original, outputs }

  // 초안을 직접 고치는 것처럼 쓰되, 실제로는 복사본을 바꿔 React가 변경을 알아채게 한다
  const edit: Edit = (change) =>
    setDraft((d) => {
      const next = structuredClone(d ?? outputs)
      change(next)
      return next
    })

  async function save() {
    if (!draft) return
    setSaving(true)
    setSaveError(null)
    try {
      onJobChange(await saveOutputs(job.id, cleanOutputs(draft)))
      setDraft(null)
    } catch (e) {
      setSaveError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  async function resetToOriginal() {
    if (!window.confirm('직접 고친 내용을 모두 지우고 AI가 만든 원본으로 되돌릴까요?')) return
    try {
      onJobChange(await resetOutputs(job.id))
    } catch (e) {
      setSaveError((e as Error).message)
    }
  }

  // 저장하지 않은 수정이 있으면 페이지를 떠나기 전에 브라우저가 한 번 묻는다
  useEffect(() => {
    if (!editing) return
    const warn = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [editing])

  const [tab, setTabState] = useState<TabKey>(() => {
    const fromUrl = new URLSearchParams(window.location.search).get('tab')
    return TABS.some((t) => t.key === fromUrl) ? (fromUrl as TabKey) : 'portfolio'
  })

  function setTab(key: TabKey) {
    setTabState(key)
    const params = new URLSearchParams(window.location.search)
    params.set('tab', key)
    window.history.replaceState(null, '', `?${params}`)
  }
  const m = projectMeta(result)
  const u = result.usage

  const stats = [
    { label: '분석 기간', value: m.period || '-' },
    { label: '분석한 커밋', value: `${m.commits}개` },
    { label: '기능 단위 작업', value: `${m.works}개` },
    { label: 'AI 호출', value: `${u.calls}회${u.cached_calls ? ` · 캐시 ${u.cached_calls}` : ''}` },
  ]

  return (
    <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5 dark:border-slate-800 dark:bg-slate-900/60">
      {/* 머리말: 레포 이름, 핵심 수치, 언어 비율 */}
      <div className="border-b border-slate-100 bg-gradient-to-br from-slate-50 to-indigo-50/60 px-5 pt-6 sm:px-8 dark:border-slate-800 dark:from-slate-900 dark:to-indigo-950/40">
        <a
          href={result.repo.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 text-xl font-bold tracking-tight hover:text-indigo-600 sm:text-2xl"
        >
          <GitHubIcon className="h-5 w-5" />
          {result.repo.owner}/{result.repo.name}
        </a>
        <p className="mt-1 text-sm text-slate-500">{result.username}의 기여 분석</p>

        <dl className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {stats.map((s) => (
            <div key={s.label} className="rounded-xl bg-white/80 px-3.5 py-2.5 ring-1 ring-slate-200/70 dark:bg-slate-900/70 dark:ring-slate-800">
              <dt className="text-[11px] font-medium text-slate-500">{s.label}</dt>
              <dd className="mt-0.5 text-sm font-semibold tabular-nums">{s.value}</dd>
            </div>
          ))}
        </dl>

        {m.languages.length > 0 && (
          <div className="mt-4">
            <div className="flex h-1.5 overflow-hidden rounded-full">
              {m.languages.map((l, i) => (
                <div key={l.name} className={LANG_COLORS[i]} style={{ width: `${l.share * 100}%` }} />
              ))}
            </div>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500">
              {m.languages.map((l, i) => (
                <span key={l.name} className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${LANG_COLORS[i]}`} />
                  {l.name} {Math.round(l.share * 100)}%
                </span>
              ))}
            </div>
          </div>
        )}

        <EditBar
          editing={editing}
          saving={saving}
          editedAt={job.edited_at}
          error={saveError}
          onStart={() => setDraft(structuredClone(outputs))}
          onSave={save}
          onCancel={() => {
            setDraft(null)
            setSaveError(null)
          }}
          onReset={resetToOriginal}
        />

        <nav className="mt-4 -mb-px flex gap-1 overflow-x-auto" role="tablist">
          {TABS.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className={`shrink-0 border-b-2 px-4 py-2.5 text-sm font-semibold whitespace-nowrap transition ${
                tab === t.key
                  ? 'border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="p-5 sm:p-8">
        {tab === 'portfolio' && <PortfolioTab result={result} edit={editing ? edit : null} />}
        {tab === 'slides' && <SlidesTab result={result} edit={editing ? edit : null} />}
        {tab === 'notes' && <NotesTab result={result} />}
      </div>
    </section>
  )
}

function EditBar(props: {
  editing: boolean
  saving: boolean
  editedAt: string | null
  error: string | null
  onStart: () => void
  onSave: () => void
  onCancel: () => void
  onReset: () => void
}) {
  const { editing, saving, editedAt, error } = props
  const btn = 'rounded-lg px-3 py-1.5 text-xs font-semibold transition'
  return (
    <div
      className={`mt-5 flex flex-wrap items-center justify-between gap-2 rounded-xl px-3.5 py-2.5 text-xs ${
        editing ? 'bg-indigo-600 text-white' : 'bg-white/70 ring-1 ring-slate-200/70 dark:bg-slate-900/60 dark:ring-slate-800'
      }`}
    >
      <p className={editing ? '' : 'text-slate-500'}>
        {editing
          ? '수정 중 · 점선 칸을 고치세요. 고친 문장에는 "직접 수정" 표시가 붙습니다.'
          : editedAt
            ? `직접 수정한 결과입니다 (${new Date(editedAt).toLocaleString('ko-KR', { dateStyle: 'short', timeStyle: 'short' })})`
            : 'AI가 만든 결과입니다. 마음에 안 들거나 사실과 다른 부분은 직접 고칠 수 있습니다.'}
        {error && <span className="ml-2 font-semibold text-red-500">저장 실패: {error}</span>}
      </p>
      <div className="flex gap-1.5">
        {editing ? (
          <>
            <button onClick={props.onCancel} className={`${btn} bg-white/15 hover:bg-white/25`}>
              취소
            </button>
            <button onClick={props.onSave} disabled={saving} className={`${btn} bg-white text-indigo-700 hover:bg-indigo-50 disabled:opacity-60`}>
              {saving ? '저장 중…' : '저장'}
            </button>
          </>
        ) : (
          <>
            {editedAt && (
              <button onClick={props.onReset} className={`${btn} text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800`}>
                AI 원본으로 되돌리기
              </button>
            )}
            <button onClick={props.onStart} className={`${btn} bg-slate-900 text-white hover:bg-slate-700 dark:bg-white dark:text-slate-900`}>
              수정하기
            </button>
          </>
        )}
      </div>
    </div>
  )
}
