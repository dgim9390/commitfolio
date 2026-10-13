// 백엔드 app/models.py와 같은 모양 (필요한 필드만)

export interface Statement {
  text: string
  evidence: string[] // 커밋 SHA
  from_readme: boolean
  warnings: string[]
}

export interface Slide {
  title: string
  bullets: Statement[]
  notes: string
}

export interface Portfolio {
  overview: string
  contributions: Statement[]
  tech_stack: string[]
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
  repo: { owner: string; name: string; url: string; description: string | null }
  username: string
  commits: CommitRef[]
  grouping: { groups: { id: number }[]; excluded: { sha: string; reason: string }[] }
  summaries: GroupSummary[]
  outputs: { portfolio: Portfolio; slides: Slide[] }
  validation_notes: string[]
  usage: { model: string; calls: number; cached_calls: number }
}

export type JobStatus = 'queued' | 'running' | 'done' | 'error'

export interface Job {
  id: string
  status: JobStatus
  stage: string | null
  message: string
  error: string | null
  result: AnalysisResult | null
}

export interface AnalyzeRequest {
  repo_url: string
  username: string
  since?: string
  until?: string
}
