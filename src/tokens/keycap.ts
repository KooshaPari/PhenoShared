/**
 * Keycap Palette — Design Tokens
 *
 * Programmatic access to the Phenotype design system colors.
 * For CSS usage, import the CSS files directly.
 */

export const keycap = {
  accent: '#7ebab5',
  accentHover: '#95ccc8',
  accentActive: '#6aa8a3',
  accentDim: '#569691',
  accentContrast: '#4a9c97',
  slate: '#353a40',

  dark: {
    bg: '#090a0c',
    bgAlt: '#0e1014',
    bgSoft: '#14171b',
    bgElv: '#1a1e24',
    text1: '#f6f5f5',
    text2: '#a8adb5',
    text3: '#6b7280',
    divider: '#1f2329',
    gutter: '#0c0d0f',
    codeBlockBg: '#060708',
  },

  light: {
    bg: '#f8f9fa',
    bgAlt: '#f0f1f3',
    bgSoft: '#e8eaed',
    bgElv: '#ffffff',
    text1: '#1a1c1e',
    text2: '#4a4f57',
    text3: '#6b7280',
    divider: '#d4d7dc',
    gutter: '#e8eaed',
    codeBlockBg: '#f0f1f3',
  },

  font: {
    base: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    mono: "'JetBrains Mono', ui-monospace, 'Cascadia Code', monospace",
  },
} as const

export type KeycapTokens = typeof keycap
