/**
 * dark-mode.js — Phenotype dark mode toggle with system preference detection.
 *
 * ============================================================
 * REQUIRED CSS ADDITIONS (to be added in styles/tokens.css)
 * ============================================================
 *
 * [data-theme="dark"] {
 *   --surface: var(--graphite-950);
 *   --ink: var(--paper-100);
 *   --surface-raised: var(--graphite-900);
 *   --ink-muted: var(--concrete-500);
 *   --rule: color-mix(in oklch, var(--paper-100) 24%, transparent);
 *   --precision-rule: color-mix(in oklch, var(--paper-100) 18%, transparent);
 *   --precision-rule-strong: color-mix(in oklch, var(--paper-100) 36%, transparent);
 *   --shadow-card: 0 1px 0 var(--precision-rule);
 *   --shadow-specimen: 0.65rem 0.65rem 0 color-mix(in oklch, var(--paper-100) 14%, transparent);
 *   --surface-inset: var(--graphite-900);
 *   color-scheme: dark;
 * }
 *
 * Accent colors (teal, olive, arch) stay unchanged.
 *
 * Also add to tokens.css:
 *
 * .theme-transitioning,
 * .theme-transitioning *,
 * .theme-transitioning *::before,
 * .theme-transitioning *::after {
 *   transition: background-color 0.3s, color 0.3s, border-color 0.3s !important;
 * }
 *
 * ============================================================
 */

const STORAGE_KEY = 'koosha-atelier-theme';
const TRANSITION_MS = 300;

/** @type {'light' | 'dark' | null} Manual override (null = follow system). */
let manualOverride = null;

/** @type {(() => void) | null} Cleanup for OS listener. */
let cleanupListener = null;

/* ------------------------------------------------------------------ */
/*  Internal helpers                                                   */
/* ------------------------------------------------------------------ */

function readStored() {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === 'light' || v === 'dark') return v;
  } catch { /* SSR / private-browsing */ }
  return null;
}

function systemPreference() {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light';
}

function resolvedTheme() {
  return manualOverride ?? systemPreference();
}

function applyToDOM(theme) {
  const root = document.documentElement;
  root.setAttribute('data-theme', theme);

  // Smooth transition — add class, remove after TRANSITION_MS
  root.classList.add('theme-transitioning');
  setTimeout(() => root.classList.remove('theme-transitioning'), TRANSITION_MS);
}

function persist(theme) {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch { /* ignore */ }
}

function updateButton(btn, theme) {
  if (!btn) return;
  const isDark = theme === 'dark';
  btn.setAttribute('aria-pressed', String(isDark));
  btn.innerHTML = isDark ? MOON_SVG : SUN_SVG;
}

/* ------------------------------------------------------------------ */
/*  SVG icons — inline, 20px viewBox, no emoji                         */
/* ------------------------------------------------------------------ */

const SUN_SVG = /*html*/ `<svg width="20" height="20" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round"
  aria-hidden="true">
  <circle cx="12" cy="12" r="5"/>
  <line x1="12" y1="1" x2="12" y2="3"/>
  <line x1="12" y1="21" x2="12" y2="23"/>
  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
  <line x1="1" y1="12" x2="3" y2="12"/>
  <line x1="21" y1="12" x2="23" y2="12"/>
  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
</svg>`;

const MOON_SVG = /*html*/ `<svg width="20" height="20" viewBox="0 0 24 24"
  fill="none" stroke="currentColor" stroke-width="2"
  stroke-linecap="round" stroke-linejoin="round"
  aria-hidden="true">
  <path d="M21 12.79A9 9 0 1 1 11.21 3
           7 7 0 0 0 21 12.79z"/>
</svg>`;

/* ------------------------------------------------------------------ */
/*  Public API                                                         */
/* ------------------------------------------------------------------ */

/**
 * Initialise the dark mode system.
 *
 * @param {object} [opts]
 * @param {HTMLElement} [opts.toolbar] — Container where the toggle button
 *   will be prepended (typically `.atelier-tools`).
 * @param {HTMLElement} [opts.insertBefore] — Insert toggle before this node
 *   inside the toolbar. Falls back to prepending.
 * @returns {{ toggle: HTMLButtonElement }} The toggle button element.
 */
export function initDarkMode({ toolbar, insertBefore } = {}) {
  // 1. Restore stored preference
  manualOverride = readStored();

  // 2. Apply initial theme before first paint (attribute must exist early)
  const initial = resolvedTheme();
  document.documentElement.setAttribute('data-theme', initial);

  // 3. Build toggle button
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'dark-mode-toggle';
  btn.setAttribute('aria-label', 'Toggle dark mode');
  btn.setAttribute('aria-pressed', String(initial === 'dark'));
  btn.innerHTML = initial === 'dark' ? MOON_SVG : SUN_SVG;

  btn.addEventListener('click', () => {
    const next = resolvedTheme() === 'dark' ? 'light' : 'dark';
    setTheme(next);
  });

  // 4. Insert into toolbar if provided
  if (toolbar) {
    if (insertBefore && insertBefore.parentNode === toolbar) {
      toolbar.insertBefore(btn, insertBefore);
    } else {
      toolbar.prepend(btn);
    }
  }

  // 5. Listen for OS preference changes (only when no manual override)
  if (typeof window !== 'undefined') {
    const mql = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e) => {
      if (manualOverride !== null) return; // user chose explicitly
      const next = e.matches ? 'dark' : 'light';
      applyToDOM(next);
      updateButton(btn, next);
    };
    mql.addEventListener('change', handler);
    cleanupListener = () => mql.removeEventListener('change', handler);
  }

  return { toggle: btn };
}

/**
 * Set the theme explicitly.
 * @param {'light' | 'dark'} theme
 */
export function setTheme(theme) {
  if (theme !== 'light' && theme !== 'dark') return;
  manualOverride = theme;
  persist(theme);
  applyToDOM(theme);

  const btn = document.querySelector('.dark-mode-toggle');
  updateButton(btn, theme);
}

/**
 * Get the currently active theme.
 * @returns {'light' | 'dark'}
 */
export function getTheme() {
  return resolvedTheme();
}
