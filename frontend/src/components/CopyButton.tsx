import { useState } from 'react'
import { CheckIcon, CopyIcon } from './icons'

export function CopyButton({
  text,
  label = '복사',
  className = '',
  primary = false,
}: {
  text: () => string
  label?: string
  className?: string
  primary?: boolean
}) {
  const [state, setState] = useState<'idle' | 'done' | 'fail'>('idle')

  async function copy() {
    try {
      await navigator.clipboard.writeText(text())
      setState('done')
    } catch {
      setState('fail')
    }
    setTimeout(() => setState('idle'), 1500)
  }

  const look = primary
    ? 'bg-slate-900 text-white hover:bg-slate-700 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-200'
    : 'border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800'

  return (
    <button type="button" onClick={copy} className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${look} ${className}`}>
      {state === 'done' ? <CheckIcon className="h-3.5 w-3.5 text-emerald-500" /> : <CopyIcon />}
      {state === 'done' ? '복사됨' : state === 'fail' ? '복사 실패' : label}
    </button>
  )
}
