/**
 * Shared visual tokens for systems-plate and case-diagram components.
 *
 * Single source of truth for node/edge colors, dimensions, and typography
 * used across Substrate architecture plates and project case-study diagrams.
 * All values are semantic; no runtime telemetry is implied.
 */

export const DIAGRAM_TOKENS = {
  /** Node rectangle */
  node: {
    fill: 'var(--surface)',
    stroke: 'var(--rule)',
    strokeWidth: 1,
    rx: 2,
    height: 48,
  },

  /** Node text */
  text: {
    fill: 'var(--ink)',
    fontSize: '0.85rem',
    fontFamily: 'var(--font-meta)',
  },

  /** Node index prefix (01, 02, ...) */
  index: {
    fill: 'var(--ink-muted)',
    fontSize: '0.78rem',
    fontFamily: 'var(--font-meta)',
  },

  /** Edge lines between nodes */
  edge: {
    stroke: 'var(--arch-500)',
    strokeWidth: 2,
  },

  /** Fallback paragraph when SVG is hidden */
  fallback: {
    color: 'var(--ink-muted)',
    fontSize: 'var(--step--1)',
    fontFamily: 'var(--font-meta)',
  },

  /** Figure caption */
  caption: {
    color: 'var(--ink-muted)',
    fontSize: 'var(--step--1)',
    fontFamily: 'var(--font-meta)',
  },

  /** Mobile breakpoint — below this, show text fallback instead of SVG */
  mobileBreakpoint: 600,
};

/**
 * Returns true if the viewport is narrower than the mobile breakpoint.
 * Safe for SSR (returns false).
 */
export function isMobileViewport(windowRef = typeof window !== 'undefined' ? window : null) {
  if (!windowRef?.matchMedia) return false;
  return windowRef.matchMedia(`(max-width: ${DIAGRAM_TOKENS.mobileBreakpoint}px)`).matches;
}
