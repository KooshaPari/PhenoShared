export type PolygonLayer = {
  readonly rotation: number
  readonly scale: number
  readonly opacity: number
}

export type PolygonPreset = {
  readonly baseShape: 'hexagon' | 'diamond' | 'pentagon' | 'triangle'
  readonly clipPath: string
  readonly layers: readonly PolygonLayer[]
}

export const POLYGONS = {
  hexagon: {
    baseShape: 'hexagon',
    clipPath: 'polygon(25% 6%, 75% 6%, 100% 50%, 75% 94%, 25% 94%, 0 50%)',
    layers: [
      { rotation: 0, scale: 1, opacity: 0.34 },
      { rotation: 4, scale: 0.94, opacity: 0.24 },
      { rotation: -3, scale: 0.88, opacity: 0.16 },
    ],
  },
  diamond: {
    baseShape: 'diamond',
    clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
    layers: [
      { rotation: 45, scale: 1, opacity: 0.3 },
      { rotation: 45, scale: 0.92, opacity: 0.2 },
      { rotation: 45, scale: 0.84, opacity: 0.12 },
    ],
  },
  pentagon: {
    baseShape: 'pentagon',
    clipPath: 'polygon(50% 0%, 95% 35%, 78% 100%, 22% 100%, 5% 35%)',
    layers: [
      { rotation: 0, scale: 1, opacity: 0.3 },
      { rotation: 8, scale: 0.92, opacity: 0.2 },
      { rotation: -6, scale: 0.84, opacity: 0.14 },
      { rotation: 0, scale: 0.76, opacity: 0.08 },
    ],
  },
  triangle: {
    baseShape: 'triangle',
    clipPath: 'polygon(50% 0%, 100% 100%, 0% 100%)',
    layers: [
      { rotation: 0, scale: 1, opacity: 0.32 },
      { rotation: 180, scale: 0.9, opacity: 0.18 },
      { rotation: 0, scale: 0.8, opacity: 0.12 },
      { rotation: 0, scale: 0.7, opacity: 0.06 },
    ],
  },
} as const satisfies Record<string, PolygonPreset>

export type Polygons = typeof POLYGONS
