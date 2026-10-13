import { useState } from 'react'

export function CopyButton({ text, label = '복사', className = '' }: { text: () => string; label?: string; className?: string }) {
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

  return (
    <button
      type="button"
      onClick={copy}
      className={`rounded-md border border-zinc-300 px-2.5 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-200 dark:hover:bg-zinc-800 ${className}`}
    >
      {state === 'done' ? '복사됨 ✓' : state === 'fail' ? '복사 실패' : label}
    </button>
  )
}
