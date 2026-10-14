import type { AnalyzeRequest, Job, Outputs } from './types'

// 접근 코드: 사이트에 ACCESS_CODE가 설정돼 있으면 모든 요청에 같이 보낸다.
// 이 브라우저에만 기억해 두는 편의 기능이라, 저장이 막힌 환경(사생활 보호 모드 등)에서도 동작하게 try로 감싼다
const CODE_KEY = 'commitfolio-access-code'

export function getAccessCode(): string {
  try {
    return localStorage.getItem(CODE_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setAccessCode(code: string) {
  try {
    if (code) localStorage.setItem(CODE_KEY, code)
    else localStorage.removeItem(CODE_KEY)
  } catch {
    // 저장이 안 되면 이번 화면에서만 쓰인다
  }
  memoryCode = code
}

let memoryCode = getAccessCode()

/** 접근 코드가 없거나 틀렸을 때 */
export class AccessDeniedError extends Error {}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, { ...init, headers: { ...init?.headers, 'X-Access-Code': memoryCode } })
  } catch {
    throw new Error('서버에 연결할 수 없습니다. 잠시 후 다시 시도하세요.')
  }
  if (res.status === 401) throw new AccessDeniedError('접근 코드가 틀렸습니다.')
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

/** 서버 설정 확인. 무료 서버는 한동안 안 쓰면 잠들어서 깨어나는 데 1분 가까이 걸리므로 몇 번 다시 시도한다 */
export async function getConfig(onWaiting?: () => void): Promise<{ access_code_required: boolean }> {
  for (let attempt = 0; ; attempt++) {
    try {
      return await request('/api/config')
    } catch (e) {
      if (attempt >= 11) throw e // 약 1분(5초 × 12번) 동안 안 깨어나면 포기
      onWaiting?.()
      await new Promise((r) => setTimeout(r, 5000))
    }
  }
}

/** 접근 코드가 맞는지 확인 (틀리면 AccessDeniedError) */
export function checkAccess(): Promise<{ ok: boolean }> {
  return request('/api/access')
}
