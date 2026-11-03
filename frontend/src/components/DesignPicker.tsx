import { COVER_LABELS, FONTS, PALETTES, PRESETS, PRESET_LABELS, SURFACES } from '../design'
import type { CoverName, Design, FontName, PaletteName, SlideThemeName, SurfaceName } from '../types'
import type { Edit } from './ResultView'

/**
 * 디자인 고르기 (편집 모드). 포트폴리오와 발표 자료가 같은 디자인을 쓴다.
 * AI가 고른 조합을 축별로 바꿀 수 있고, 추천 조합을 누르면 네 축이 한 번에 바뀐다.
 */
export function DesignPicker({ design, edit }: { design: Design; edit: Edit }) {
  const set = (patch: Partial<Design>) => edit((d) => void (d.design = { ...design, ...patch }))
  const chip = (on: boolean) =>
    `rounded-lg border px-2.5 py-1.5 text-xs font-medium transition ${
      on
        ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300'
        : 'border-slate-200 text-slate-600 hover:border-slate-300 dark:border-slate-700 dark:text-slate-300'
    }`

  return (
    <div className="space-y-3 rounded-xl border border-slate-200 p-4 dark:border-slate-800">
      <p className="text-xs font-semibold text-slate-500">디자인 (포트폴리오·발표 자료 공통)</p>

      <Axis label="추천 조합">
        {(Object.keys(PRESETS) as SlideThemeName[]).map((name) => {
          const p = PRESETS[name]
          const on = p.palette === design.palette && p.surface === design.surface && p.font === design.font && p.cover === design.cover
          return (
            <button key={name} type="button" aria-pressed={on} onClick={() => set(p)} className={`${chip(on)} flex items-center gap-1.5`}>
              <span className="h-3 w-3 rounded-full" style={{ background: PALETTES[p.palette].base }} />
              {PRESET_LABELS[name]}
            </button>
          )
        })}
      </Axis>

      <Axis label="색">
        <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="색 계열">
          {(Object.keys(PALETTES) as PaletteName[]).map((name) => (
            <button
              key={name}
              type="button"
              role="radio"
              aria-checked={design.palette === name}
              aria-label={PALETTES[name].label}
              title={PALETTES[name].label}
              onClick={() => set({ palette: name })}
              style={{ background: PALETTES[name].base }}
              className={`h-7 w-7 rounded-full transition ${
                design.palette === name ? 'ring-2 ring-indigo-500 ring-offset-2 dark:ring-offset-slate-900' : 'opacity-70 hover:opacity-100'
              }`}
            />
          ))}
        </div>
      </Axis>

      <Axis label="배경">
        {(Object.keys(SURFACES) as SurfaceName[]).map((name) => (
          <button key={name} type="button" aria-pressed={design.surface === name} onClick={() => set({ surface: name })} className={chip(design.surface === name)}>
            {SURFACES[name].label}
          </button>
        ))}
      </Axis>

      <Axis label="글꼴">
        {(Object.keys(FONTS) as FontName[]).map((name) => (
          <button
            key={name}
            type="button"
            aria-pressed={design.font === name}
            onClick={() => set({ font: name })}
            style={{ fontFamily: FONTS[name].heading }}
            className={chip(design.font === name)}
          >
            {FONTS[name].label}
          </button>
        ))}
      </Axis>

      <Axis label="표지">
        {(Object.keys(COVER_LABELS) as CoverName[]).map((name) => (
          <button key={name} type="button" aria-pressed={design.cover === name} onClick={() => set({ cover: name })} className={chip(design.cover === name)}>
            {COVER_LABELS[name]}
          </button>
        ))}
      </Axis>
    </div>
  )
}

function Axis({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
      <p className="w-16 shrink-0 text-[11px] font-medium text-slate-400">{label}</p>
      <div className="flex flex-wrap items-center gap-1.5">{children}</div>
    </div>
  )
}
