// 작은 인라인 아이콘들 (아이콘 라이브러리 없이)
type P = { className?: string }
const base = { fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' } as const

export const GitHubIcon = ({ className = 'h-4 w-4' }: P) => (
  <svg viewBox="0 0 16 16" className={className} fill="currentColor" aria-hidden>
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
  </svg>
)
export const CheckIcon = ({ className = 'h-4 w-4' }: P) => (
  <svg viewBox="0 0 24 24" className={className} {...base} aria-hidden>
    <path d="M20 6 9 17l-5-5" />
  </svg>
)
export const ArrowRightIcon = ({ className = 'h-4 w-4' }: P) => (
  <svg viewBox="0 0 24 24" className={className} {...base} aria-hidden>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
)
export const SparkIcon = ({ className = 'h-4 w-4' }: P) => (
  <svg viewBox="0 0 24 24" className={className} {...base} aria-hidden>
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6.3 6.3l2.8 2.8M14.9 14.9l2.8 2.8M6.3 17.7l2.8-2.8M14.9 9.1l2.8-2.8" />
  </svg>
)
export const CopyIcon = ({ className = 'h-3.5 w-3.5' }: P) => (
  <svg viewBox="0 0 24 24" className={className} {...base} aria-hidden>
    <rect x="9" y="9" width="12" height="12" rx="2" />
    <path d="M5 15V5a2 2 0 0 1 2-2h10" />
  </svg>
)
export const DownloadIcon = ({ className = 'h-3.5 w-3.5' }: P) => (
  <svg viewBox="0 0 24 24" className={className} {...base} aria-hidden>
    <path d="M12 3v12M7 10l5 5 5-5M5 21h14" />
  </svg>
)
export const ExpandIcon = ({ className = 'h-3.5 w-3.5' }: P) => (
  <svg viewBox="0 0 24 24" className={className} {...base} aria-hidden>
    <path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3" />
  </svg>
)
export const AlertIcon = ({ className = 'h-3.5 w-3.5' }: P) => (
  <svg viewBox="0 0 24 24" className={className} {...base} aria-hidden>
    <path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
  </svg>
)
