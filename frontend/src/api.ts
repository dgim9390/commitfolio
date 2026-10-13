import type { AnalyzeRequest, Job, Outputs } from './types'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, init)
  } catch {
    throw new Error('서버에 연결할 수 없습니다. 백엔드(uvicorn)가 켜져 있는지 확인하세요.')
  }
  if (!res.ok) {
    // FastAPI는 에러를 {detail: ...} 로 보낸다 (입력 검증 실패면 detail이 배열)
    const body = await res.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : `요청 실패 (${res.status})`
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export function startAnalysis(req: AnalyzeRequest): Promise<{ job_id: string }> {
  return request('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
}

export function getJob(jobId: string): Promise<Job> {
  return request(`/api/jobs/${jobId}`)
}

/** 직접 고친 결과 저장 */
export function saveOutputs(jobId: string, outputs: Outputs): Promise<Job> {
  return request(`/api/jobs/${jobId}/outputs`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(outputs),
  })
}

/** 직접 고친 내용을 버리고 AI 원본으로 */
export function resetOutputs(jobId: string): Promise<Job> {
  return request(`/api/jobs/${jobId}/outputs`, { method: 'DELETE' })
}
