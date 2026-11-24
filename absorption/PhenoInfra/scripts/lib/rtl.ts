/**
 * AT5 — Shared RTL helper.
 *
 * Used by tests, scripts, and any future runtime code that needs to
 * branch on a locale's reading direction. Kept tiny and dependency-free
 * so it can be imported from both Node scripts and VitePress Vue
 * components (Vite handles the .ts → .js transpile).
 */
const RTL_LOCALES = new Set(['ar', 'he', 'fa', 'ur'])

export function isRtl(locale: string | undefined | null): boolean {
  if (!locale) return false
  const root = locale.toLowerCase().split('-')[0]
  return RTL_LOCALES.has(root)
}

export function dirFor(locale: string | undefined | null): 'ltr' | 'rtl' {
  return isRtl(locale) ? 'rtl' : 'ltr'
}

export const RTL_LOCALES_LIST = [...RTL_LOCALES] as const
