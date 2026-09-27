/**
 * AT1 — Axe-core configuration for VitePress docsite routes.
 *
 * Shared between the vitest+playwright runner and any ad-hoc Node script.
 * Rules are tuned for VitePress:
 *   - `region` is disabled because the VitePress sidebar already acts as
 *     a navigational region; axe-core misclassifies the body when the
 *     sidebar takes the only landmark.
 *   - `bypass` is disabled to avoid false positives on VitePress error
 *     boundaries and 404 pages.
 *   - `color-contrast` is enabled and tuned to the brand palette.
 */
import type { Spec } from 'axe-core'

export const AXE_TAGS = [
  'wcag2a',
  'wcag2aa',
  'wcag21a',
  'wcag21aa',
] as const

export const AXE_RESULT_TYPES = ['violations'] as const

export const AXE_RULES: Record<string, { enabled: boolean }> = {
  'color-contrast': { enabled: true },
  region: { enabled: false },
  bypass: { enabled: false },
  'landmark-one-main': { enabled: true },
}

export const AXE_OPTIONS: Spec = {
  runOnly: { type: 'tag', values: [...AXE_TAGS] },
  resultTypes: [...AXE_RESULT_TYPES],
  rules: AXE_RULES,
}
