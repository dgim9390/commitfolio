import { SLIDE_THEMES, THEME_NAMES } from '../slideThemes'
import type { SlideThemeName } from '../types'
import type { Edit } from './ResultView'

/** 테마 고르기 (편집 모드). 포트폴리오와 발표 자료가 같은 테마를 쓴다 */
export function ThemePicker({ theme, edit }: { theme: SlideThemeName; edit: Edit }) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold text-slate-500">테마 (포트폴리오·발표 자료 공통)</p>
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="테마">
        {THEME_NAMES.map((name) => (
          <button
            key={name}
            type="button"
            role="radio"
            aria-checked={theme === name}
            title={SLIDE_THEMES[name].description}
            onClick={() => edit((d) => void (d.theme = name))}
            className={`flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${
              theme === name
                ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300'
                : 'border-slate-200 text-slate-600 hover:border-slate-300 dark:border-slate-700 dark:text-slate-300'
            }`}
          >
            {/* 버튼마다 그 테마의 표지 색을 작게 보여준다 */}
            <span className={`h-4 w-6 rounded ${SLIDE_THEMES[name].cover.bg}`} />
            {SLIDE_THEMES[name].label}
          </button>
        ))}
      </div>
    </div>
  )
}
