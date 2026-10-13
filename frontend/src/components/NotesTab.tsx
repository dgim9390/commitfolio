import type { AnalysisResult } from '../types'

const EXCLUDE_LABELS: Record<string, string> = {
  docs_only: '문서만 수정',
  version_bump: '버전 번호만 변경',
  no_code: '분석할 파일 없음',
}

/** 결과가 어떻게 만들어졌는지: 작업 그룹 요약, 분석에서 뺀 커밋, 검증 메모 */
export function NotesTab({ result }: { result: AnalysisResult }) {
  const commits = new Map(result.commits.map((c) => [c.sha, c]))
  return (
    <div className="space-y-6 text-sm">
      <section>
        <h3 className="mb-2 font-semibold text-zinc-500">작업 그룹 ({result.summaries.length}개)</h3>
        <ul className="space-y-2">
          {result.summaries.map((s) => (
            <li key={s.group_id}>
              <span className="font-medium">{s.title}</span>{' '}
              <span className={`text-xs ${s.significance === 'major' ? 'text-indigo-600' : 'text-zinc-400'}`}>{s.significance}</span>
              <span className="text-zinc-400"> · 커밋 {s.evidence.length}개</span>
              <p className="mt-0.5 text-zinc-600 dark:text-zinc-400">{s.solution}</p>
            </li>
          ))}
        </ul>
      </section>

      {result.grouping.excluded.length > 0 && (
        <section>
          <h3 className="mb-2 font-semibold text-zinc-500">분석에서 뺀 커밋</h3>
          <ul className="space-y-1">
            {result.grouping.excluded.map((e) => {
              const c = commits.get(e.sha)
              return (
                <li key={e.sha} className="text-zinc-600 dark:text-zinc-400">
                  <a href={c?.url} target="_blank" rel="noreferrer" className="font-mono text-xs hover:underline">
                    {e.sha.slice(0, 7)}
                  </a>{' '}
                  {c?.title} <span className="text-zinc-400">— {EXCLUDE_LABELS[e.reason] ?? e.reason}</span>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      <section>
        <h3 className="mb-2 font-semibold text-zinc-500">검증 메모</h3>
        {result.validation_notes.length === 0 ? (
          <p className="text-zinc-400">AI가 쓴 문장에서 문제를 발견하지 못했습니다.</p>
        ) : (
          <ul className="list-disc space-y-1 pl-5 text-zinc-600 dark:text-zinc-400">
            {result.validation_notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
