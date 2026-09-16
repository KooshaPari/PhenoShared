import { keycap } from './keycap'
import { glass } from './glass'
import { typography } from './typography'
import { MATERIALS } from './materials'
import { POLYGONS } from './polygons'
import { NEUMORPHISM } from './neumorphism'

export { keycap, type KeycapTokens } from './keycap'
export { glass, type GlassTokens } from './glass'
export { typography, type TypographyTokens } from './typography'
export { MATERIALS, type Materials } from './materials'
export { POLYGONS, type PolygonLayer, type PolygonPreset, type Polygons } from './polygons'
export { NEUMORPHISM, type Neumorphism } from './neumorphism'

export const designTokens = {
  keycap,
  glass,
  typography,
  materials: MATERIALS,
  polygons: POLYGONS,
  neumorphism: NEUMORPHISM,
} as const

export type DesignTokens = typeof designTokens
