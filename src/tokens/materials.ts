export const MATERIALS = {
  windows: {
    base: 'mica',
    acrylic: 'rgba(9,10,12,0.7) + backdrop-blur(20px) + saturate(180%)',
    card: 'rgba(126,186,181,0.08) + border: 1px solid rgba(126,186,181,0.15)',
  },
  macos: {
    base: 'liquid-glass',
    vibrancy: 'rgba(126,186,181,0.12) + backdrop-filter: blur(40px) saturate(200%) brightness(1.1)',
    chromaShift: '1px rgba(126,186,181,0.3)',
  },
  android: {
    base: 'material-you',
    surface: 'linear-gradient(135deg, #0d1117 0%, #161b22 100%)',
    card: 'rgba(126,186,181,0.06) + border: 1px solid rgba(126,186,181,0.1)',
  },
  web: {
    base: 'glassmorphism',
    panel: 'rgba(9,10,12,0.6) + backdrop-filter: blur(16px) saturate(150%)',
    border: '1px solid rgba(126,186,181,0.2)',
  },
} as const

export type Materials = typeof MATERIALS
