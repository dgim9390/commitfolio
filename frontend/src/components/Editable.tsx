// 편집 모드에서 쓰는 입력 칸들. 평소 글자와 같은 크기·굵기로 보이게 해서
// "그 자리에서 고친다"는 느낌을 주고, 점선 테두리로 고칠 수 있는 곳임을 표시한다.

const box =
  'w-full rounded-lg border border-dashed border-indigo-300 bg-indigo-50/40 px-2 py-1 outline-none transition focus:border-solid focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 dark:border-indigo-800 dark:bg-indigo-950/20 dark:focus:bg-slate-900'

export function EditText({
  value,
  onChange,
  multiline = false,
  className = '',
  placeholder,
  label,
}: {
  value: string
  onChange: (v: string) => void
  multiline?: boolean
  className?: string
  placeholder?: string
  label: string // 화면 낭독기용 이름
}) {
  if (multiline) {
    return (
      <textarea
        aria-label={label}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        rows={2}
        // field-sizing: 글 길이에 맞춰 높이가 자동으로 늘어난다 (지원 안 하는 브라우저는 2줄 + 크기 조절)
        className={`${box} resize-y [field-sizing:content] ${className}`}
      />
    )
  }
  return (
    <input aria-label={label} value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} className={`${box} ${className}`} />
  )
}

/** 쉼표로 구분한 목록 (기술 태그 등) */
export function EditList({ items, onChange, label, placeholder }: { items: string[]; onChange: (v: string[]) => void; label: string; placeholder?: string }) {
  return (
    <EditText
      label={label}
      placeholder={placeholder ?? '쉼표로 구분 (예: React, three.js)'}
      value={items.join(', ')}
      onChange={(v) => onChange(v.split(',').map((x) => x.trimStart()))}
      className="text-sm"
    />
  )
}

export function RemoveButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="shrink-0 rounded-md px-1.5 py-1 text-xs text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/40"
    >
      삭제
    </button>
  )
}

export function AddButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-500 hover:border-indigo-400 hover:text-indigo-600 dark:border-slate-700"
    >
      + {children}
    </button>
  )
}
