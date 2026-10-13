import { useState } from 'react'

/** 접근 코드를 아는 사람만 쓰도록 설정된 사이트에서 처음 보이는 화면 */
export function AccessGate({ error, onSubmit }: { error: string | null; onSubmit: (code: string) => void }) {
  const [code, setCode] = useState('')
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (code.trim()) onSubmit(code.trim())
      }}
      className="mx-auto max-w-sm space-y-4 rounded-2xl border border-slate-200 bg-white/80 p-6 shadow-xl shadow-indigo-900/5 backdrop-blur dark:border-slate-800 dark:bg-slate-900/70"
    >
      <div>
        <p className="font-semibold">접근 코드를 입력하세요</p>
        <p className="mt-1 text-sm text-slate-500">초대받은 사람만 사용할 수 있는 사이트입니다.</p>
      </div>
      <input
        type="password"
        autoFocus
        aria-label="접근 코드"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        className="w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/15 dark:border-slate-700 dark:bg-slate-900"
      />
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      <button className="w-full rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 py-2.5 text-sm font-semibold text-white hover:brightness-110">
        들어가기
      </button>
    </form>
  )
}
