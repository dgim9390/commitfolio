// 백엔드 app/models.py와 같은 모양 (필요한 필드만)

export interface Statement {
  text: string
  evidence: string[] // 커밋 SHA
  from_readme: boolean
  warnings: string[]
  edited?: boolean // 사용자가 직접 고치거나 추가한 문장
}

export interface SlidePoint extends Statement {
  heading: string
}

export interface Highlight {
  value: string
  label: string
  evidence: string[]
  from_readme: boolean
}

export type SlideLayout = 'cover' | 'agenda' | 'problem' | 'feature' | 'architecture' | 'tech' | 'summary'

export interface Slide {
  layout: SlideLayout
  title: string
  headline: string
  points: SlidePoint[]
  highlights: Highlight[]
  flow: string[]
  notes: string
}

export interface Contribution {
  title: string
  background?: Statement | null // 배경: 왜 필요했는지 (예전 결과에는 없다)
  summary: Statement // 한 일
  points: Statement[] // 구현 포인트
  outcome?: Statement | null // 결과: 근거로 확인된 것만 (없으면 생략)
  technologies: string[]
}

export interface Portfolio {
  tagline: string
  overview: string
  contributions: Contribution[]
  tech_stack: { category: string; items: string[] }[]
}

// 디자인 네 축 (design.ts에서 CSS 변수로 풀어 쓴다)
export type PaletteName =
  | 'indigo' | 'violet' | 'blue' | 'sky' | 'cyan' | 'teal' | 'emerald' | 'green'
  | 'lime' | 'amber' | 'orange' | 'rose' | 'fuchsia' | 'slate' | 'stone'
export type SurfaceName = 'light' | 'tint' | 'paper' | 'ink' | 'dark'
export type FontName = 'sans' | 'serif' | 'mono' | 'display'
export type CoverName = 'glow' | 'terminal' | 'paper' | 'mono'

export interface Design {
  palette: PaletteName
  surface: SurfaceName
  font: FontName
  cover: CoverName
}

// 예전 테마 이름. design이 없는 옛 결과를 조합으로 바꿀 때만 쓴다
export type SlideThemeName = 'aurora' | 'terminal' | 'paper' | 'sunset' | 'ocean' | 'mono' | 'forest'

export interface Outputs {
  portfolio: Portfolio
  slides: Slide[]
  design?: Design | null
  theme?: SlideThemeName | null // 예전 결과 (design이 없을 때 조합으로 변환)
}

export interface CommitRef {
  sha: string
  url: string
  title: string
  authored_at: string
}

export interface GroupSummary {
  group_id: number
  title: string
  solution: string
  significance: 'major' | 'minor'
  evidence: string[]
}

export interface AnalysisResult {
  repo: { owner: string; name: string; url: string; description: string | null; languages: Record<string, number>; topics: string[] }
  since: string | null
  until: string | null
  username: string
  commits: CommitRef[]
  grouping: { groups: { id: number }[]; excluded: { sha: string; reason: string }[] }
  summaries: GroupSummary[]
  outputs: Outputs
  validation_notes: string[]
  usage: { model: string; calls: number; cached_calls: number }
}

export type JobStatus = 'queued' | 'running' | 'done' | 'error'

export interface Job {
  id: string
  request: AnalyzeRequest
  status: JobStatus
  stage: string | null
  message: string
  error: string | null
  result: AnalysisResult | null
  edited_outputs: Outputs | null // 사용자가 직접 고친 결과 (없으면 result.outputs가 AI 원본)
  edited_at: string | null
}

export interface AnalyzeRequest {
  repo_url: string
  username: string
  since?: string
  until?: string
}
