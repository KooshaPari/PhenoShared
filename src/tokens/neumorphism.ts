export const NEUMORPHISM = {
  lightSource: '315deg',
  extrudeDepth: '4px',
  shadow:
    '4px 4px 8px rgba(0,0,0,0.5), -4px -4px 8px rgba(126,186,181,0.1)',
  shadowOffset: '4px',
  highlightOffset: '-4px',
} as const

export type Neumorphism = typeof NEUMORPHISM
