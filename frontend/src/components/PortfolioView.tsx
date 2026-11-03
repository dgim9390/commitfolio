import { designOf, resolveTheme, type Theme } from '../design'
import { statementText } from '../format'
import type { AnalysisResult, Contribution, Statement } from '../types'
import { CopyButton } from './CopyButton'
import { Evidence } from './Evidence'
import { CheckIcon } from './icons'

/**
 * 디자인이 적용된 포트폴리오 페이지 (보기 전용).
 * 발표 자료와 같은 디자인 조합을 써서 레포마다 다른 분위기로 보인다.
 * 색·글꼴은 design.ts가 CSS 변수로 내려 주므로 앱의 밝은/어두운 모드와 상관없이 같은 모습이다.
 *
 * 기여 하나는 "배경 → 한 일 → 결과" 순서로 읽히게 묶는다.
 */
export function PortfolioView({ result, withLinks }: { result: AnalysisResult; withLinks: boolean }) {
  const t = resolveTheme(designOf(result.outputs))
  const p = result.outputs.portfolio
  const surface = t.dark ? 'dark' : 'light'

  return (
    <article style={t.vars} className={`overflow-hidden rounded-2xl shadow-sm ring-1 ring-black/5 ${t.page}`}>
      <Hero t={t} result={result} />

      <div className="space-y-12 px-6 py-10 sm:px-10">
        <section>
          <Kicker t={t}>OVERVIEW</Kicker>
          <p className={`mt-3 max-w-3xl text-[15px] leading-7 ${t.muted}`}>{p.overview}</p>
        </section>

        <section>
          <Kicker t={t}>KEY CONTRIBUTIONS</Kicker>
          <h3 className={`mt-1 text-xl ${t.heading}`}>주요 기여</h3>
          <ol className="mt-5 grid gap-4">
            {p.contributions.map((c, i) => (
              <ContributionCard key={i} c={c} index={i} t={t} result={result} withLinks={withLinks} surface={surface} />
            ))}
          </ol>
        </section>

        <section>
          <Kicker t={t}>TECH STACK</Kicker>
          <h3 className={`mt-1 text-xl ${t.heading}`}>기술 스택</h3>
          <dl className={`mt-5 border-t ${t.divider}`}>
            {p.tech_stack.map((g) => (
              <div key={g.category} className={`grid gap-2 border-b py-3.5 sm:grid-cols-[180px_1fr] sm:items-center ${t.divider}`}>
                <dt className={`text-sm font-semibold ${t.kicker}`}>{g.category}</dt>
                <dd className="flex flex-wrap gap-1.5">
                  {g.items.map((item) => (
                    <span key={item} className={`rounded-md px-2 py-0.5 text-[13px] ${t.chip}`}>
                      {item}
                    </span>
                  ))}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </article>
  )
}

function Kicker({ t, children }: { t: Theme; children: React.ReactNode }) {
  return <p className={`text-xs font-semibold tracking-[0.2em] ${t.kicker}`}>{children}</p>
}

/** 맨 위 머리말: 발표 자료 표지와 같은 네 가지 방식 */
function Hero({ t, result }: { t: Theme; result: AnalysisResult }) {
  const c = t.cover
  const p = result.outputs.portfolio
  const name = result.repo.name
  const path = `${result.repo.owner}/${result.repo.name}`

  if (c.style === 'terminal') {
    return (
      <header className={`px-6 py-8 sm:px-10 ${c.bg}`}>
        <div className={`overflow-hidden rounded-xl ${c.ring}`}>
          <div className={`flex items-center gap-1.5 border-b px-4 py-2.5 ${c.line} ${c.fill}`}>
            {['bg-red-400/80', 'bg-amber-300/80', 'bg-emerald-400/80'].map((dot) => (
              <span key={dot} className={`h-2.5 w-2.5 rounded-full ${dot}`} />
            ))}
            <span className={`ml-2 font-mono text-xs ${c.dim}`}>~/{path}</span>
          </div>
          <div className="px-6 py-8">
            <p className={`text-sm ${c.label}`}>$ cat portfolio.md</p>
            <h2 className={`mt-3 text-4xl sm:text-5xl ${c.title}`}>{name}</h2>
            <p className={`mt-3 font-mono text-sm ${c.sub}`}># {p.tagline}</p>
          </div>
        </div>
      </header>
    )
  }

  if (c.style === 'paper') {
    return (
      <header className={`px-6 pt-10 pb-8 sm:px-10 ${c.bg}`}>
        <div className={`flex items-baseline justify-between border-b-2 pb-2 ${c.line}`}>
          <p className={`text-sm ${c.label}`}>Portfolio</p>
          <p className={`text-xs ${c.dim}`}>{path}</p>
        </div>
        <h2 className={`mt-8 text-4xl sm:text-5xl ${c.title}`}>{name}</h2>
        <p className={`mt-3 text-lg ${c.sub}`}>{p.tagline}</p>
      </header>
    )
  }

  if (c.style === 'mono') {
    return (
      <header className={`px-6 py-10 sm:px-10 ${c.bg}`}>
        <p className={`text-xs font-semibold tracking-[0.3em] ${c.label}`}>{result.repo.owner.toUpperCase()}</p>
        <div className={`mt-8 mb-4 h-1.5 w-16 ${c.caret}`} />
        <h2 className={`text-5xl sm:text-6xl ${c.title}`}>{name}</h2>
        <p className={`mt-3 text-lg ${c.sub}`}>{p.tagline}</p>
      </header>
    )
  }

  return (
    <header className={`relative overflow-hidden px-6 py-10 sm:px-10 ${c.bg}`}>
      <div className={`absolute -top-1/2 -right-20 h-72 w-72 rounded-full blur-3xl ${c.glowA}`} />
      <div className={`absolute -bottom-1/2 -left-10 h-64 w-64 rounded-full blur-3xl ${c.glowB}`} />
      <p className={`relative text-xs font-semibold tracking-[0.25em] ${c.label}`}>PORTFOLIO · {result.repo.owner}</p>
      <h2 className={`relative mt-6 text-4xl sm:text-5xl ${c.title}`}>{name}</h2>
      <p className={`relative mt-3 text-lg ${c.sub}`}>{p.tagline}</p>
    </header>
  )
}

/** 배경·한 일·결과를 같은 라벨 폭으로 맞춰서 세 단이 눈에 바로 들어오게 한다 */
function Row({ t, label, children }: { t: Theme; label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[3.75rem_1fr] sm:gap-3">
      <p className={`pt-0.5 text-xs font-semibold tracking-wide ${t.kicker}`}>{label}</p>
      <div className="min-w-0">{children}</div>
    </div>
  )
}

function ContributionCard({
  c,
  index,
  t,
  result,
  withLinks,
  surface,
}: {
  c: Contribution
  index: number
  t: Theme
  result: AnalysisResult
  withLinks: boolean
  surface: 'light' | 'dark'
}) {
  const filled = (s?: Statement | null) => (s && s.text.trim() ? s : null)
  const background = filled(c.background)
  const outcome = filled(c.outcome)
  const copyText = () =>
    [
      c.title,
      ...(background ? [`배경: ${statementText(background, result, withLinks)}`] : []),
      `한 일: ${statementText(c.summary, result, withLinks)}`,
      ...c.points.map((p) => `- ${statementText(p, result, withLinks)}`),
      ...(outcome ? [`결과: ${statementText(outcome, result, withLinks)}`] : []),
    ].join('\n')

  return (
    <li className={`group rounded-2xl p-5 sm:p-6 ${t.card}`}>
      <div className="flex items-start gap-4">
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-sm font-bold ${t.badge}`}>
          {String(index + 1).padStart(2, '0')}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <h4 className={`text-lg leading-tight ${t.heading}`}>{c.title}</h4>
            <CopyButton text={copyText} className="shrink-0 sm:opacity-0 sm:group-hover:opacity-100 sm:focus:opacity-100" />
          </div>

          <div className="mt-3 space-y-3">
            {background && (
              <Row t={t} label="배경">
                <p className={`text-[15px] leading-7 ${t.muted}`}>{background.text}</p>
                <Evidence statement={background} result={result} surface={surface} />
              </Row>
            )}

            <Row t={t} label="한 일">
              <p className="leading-7">{c.summary.text}</p>
              <Evidence statement={c.summary} result={result} surface={surface} />
              {c.points.length > 0 && (
                <ul className="mt-3 space-y-2.5">
                  {c.points.map((p, i) => (
                    <li key={i} className="flex gap-2.5">
                      <CheckIcon className={`mt-1 h-4 w-4 shrink-0 ${t.kicker}`} />
                      <div className="min-w-0">
                        <p className={`text-[15px] leading-6 ${t.muted}`}>{p.text}</p>
                        <Evidence statement={p} result={result} surface={surface} />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Row>

            {outcome && (
              <Row t={t} label="결과">
                <p className="leading-7 font-medium">{outcome.text}</p>
                <Evidence statement={outcome} result={result} surface={surface} />
              </Row>
            )}
          </div>

          {c.technologies.length > 0 && (
            <div className={`mt-4 flex flex-wrap gap-1.5 border-t pt-4 ${t.divider}`}>
              {c.technologies.map((tech) => (
                <span key={tech} className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${t.chip}`}>
                  {tech}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </li>
  )
}
