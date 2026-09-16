/** Typography stacks */
export const typography = {
  fontDisplay: "'Bricolage Grotesque', 'Montserrat', sans-serif",
  fontBase: "'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  fontMono: "'JetBrains Mono', ui-monospace, 'Cascadia Code', monospace",

  scale: {
    display: { size: 96, weight: 700, letterSpacing: '-0.045em', lineHeight: 0.95, opsz: 96 },
    h1:      { size: 56, weight: 700, letterSpacing: '-0.035em', lineHeight: 1.0,  opsz: 56 },
    h2:      { size: 36, weight: 800, letterSpacing: '-0.03em',  lineHeight: 1.1 },
    h3:      { size: 22, weight: 600, letterSpacing: '-0.015em', lineHeight: 1.25 },
    body:    { size: 16, weight: 400, letterSpacing: '0',        lineHeight: 1.7 },
    small:   { size: 13, weight: 500, letterSpacing: '0.01em',   lineHeight: 1.5 },
    mono:    { size: 13, weight: 500, letterSpacing: '0',        lineHeight: 1.6 },
    eyebrow: { size: 11, weight: 600, letterSpacing: '0.18em',   lineHeight: 1.4 },
  },
} as const

export type TypographyTokens = typeof typography
