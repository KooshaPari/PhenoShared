/**
 * Design Token Tests
 *
 * Traces to: FR-DESIGN-001 (token definitions), FR-DESIGN-002 (WCAG contrast)
 *
 * Verifies:
 * - All expected token keys are present in the keycap object
 * - Color values are valid hex strings
 * - Accent/background color contrast ratios meet WCAG AA (4.5:1 for normal text)
 * - OS-adaptive material, polygon, and neumorphism tokens have the expected structure
 */

import { describe, it, expect } from 'vitest'
import { keycap, glass, typography, MATERIALS, POLYGONS, NEUMORPHISM, designTokens } from '../src/tokens'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Parse a 6-digit or 3-digit hex color string into relative luminance [0..1] */
function hexToRelativeLuminance(hex: string): number {
  const clean = hex.replace('#', '')
  const full = clean.length === 3
    ? clean.split('').map((c) => c + c).join('')
    : clean

  const r = parseInt(full.slice(0, 2), 16) / 255
  const g = parseInt(full.slice(2, 4), 16) / 255
  const b = parseInt(full.slice(4, 6), 16) / 255

  const linearize = (v: number): number =>
    v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)

  return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
}

/** WCAG contrast ratio between two hex colors */
function contrastRatio(hex1: string, hex2: string): number {
  const l1 = hexToRelativeLuminance(hex1)
  const l2 = hexToRelativeLuminance(hex2)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)
  return (lighter + 0.05) / (darker + 0.05)
}

const HEX_RE = /^#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?$/

// ---------------------------------------------------------------------------
// Token structure
// ---------------------------------------------------------------------------

describe('keycap tokens — structure', () => {
  it('exports a keycap object', () => {
    expect(keycap).toBeDefined()
    expect(typeof keycap).toBe('object')
  })

  it('has top-level accent colors', () => {
    const accentKeys = ['accent', 'accentHover', 'accentActive', 'accentDim', 'accentContrast'] as const
    for (const key of accentKeys) {
      expect(keycap).toHaveProperty(key)
      expect(typeof keycap[key]).toBe('string')
    }
  })

  it('has slate token', () => {
    expect(keycap).toHaveProperty('slate')
    expect(typeof keycap.slate).toBe('string')
  })

  it('has dark mode tokens', () => {
    const darkKeys = ['bg', 'bgAlt', 'bgSoft', 'bgElv', 'text1', 'text2', 'text3', 'divider', 'gutter', 'codeBlockBg'] as const
    for (const key of darkKeys) {
      expect(keycap.dark).toHaveProperty(key)
    }
  })

  it('has light mode tokens', () => {
    const lightKeys = ['bg', 'bgAlt', 'bgSoft', 'bgElv', 'text1', 'text2', 'text3', 'divider', 'gutter', 'codeBlockBg'] as const
    for (const key of lightKeys) {
      expect(keycap.light).toHaveProperty(key)
    }
  })

  it('has font tokens', () => {
    expect(keycap.font).toHaveProperty('base')
    expect(keycap.font).toHaveProperty('mono')
    expect(typeof keycap.font.base).toBe('string')
    expect(typeof keycap.font.mono).toBe('string')
  })

  it('merges into the top-level design token bundle', () => {
    expect(designTokens.keycap).toBe(keycap)
    expect(designTokens.materials).toBe(MATERIALS)
    expect(designTokens.polygons).toBe(POLYGONS)
    expect(designTokens.neumorphism).toBe(NEUMORPHISM)
    expect(designTokens.glass.neo.blur).toBe(16)
    expect(designTokens.typography.fontMono).toContain('JetBrains Mono')
  })
})

// ---------------------------------------------------------------------------
// Color format validation
// ---------------------------------------------------------------------------

describe('keycap tokens — color format', () => {
  const hexColorEntries: [string, string][] = [
    ['accent', keycap.accent],
    ['accentHover', keycap.accentHover],
    ['accentActive', keycap.accentActive],
    ['accentDim', keycap.accentDim],
    ['accentContrast', keycap.accentContrast],
    ['slate', keycap.slate],
    // Dark mode
    ['dark.bg', keycap.dark.bg],
    ['dark.bgAlt', keycap.dark.bgAlt],
    ['dark.bgSoft', keycap.dark.bgSoft],
    ['dark.bgElv', keycap.dark.bgElv],
    ['dark.text1', keycap.dark.text1],
    ['dark.text2', keycap.dark.text2],
    ['dark.text3', keycap.dark.text3],
    ['dark.divider', keycap.dark.divider],
    // Light mode
    ['light.bg', keycap.light.bg],
    ['light.bgElv', keycap.light.bgElv],
    ['light.text1', keycap.light.text1],
    ['light.text2', keycap.light.text2],
  ]

  for (const [name, value] of hexColorEntries) {
    it(`${name} is a valid hex color`, () => {
      expect(value).toMatch(HEX_RE)
    })
  }
})

// ---------------------------------------------------------------------------
// WCAG AA contrast checks
// ---------------------------------------------------------------------------

describe('keycap tokens — WCAG AA contrast (4.5:1 minimum)', () => {
  it('dark mode: text1 on bg meets AA', () => {
    const ratio = contrastRatio(keycap.dark.text1, keycap.dark.bg)
    expect(ratio).toBeGreaterThanOrEqual(4.5)
  })

  it('dark mode: text1 on bgElv meets AA', () => {
    const ratio = contrastRatio(keycap.dark.text1, keycap.dark.bgElv)
    expect(ratio).toBeGreaterThanOrEqual(4.5)
  })

  it('light mode: text1 on bg meets AA', () => {
    const ratio = contrastRatio(keycap.light.text1, keycap.light.bg)
    expect(ratio).toBeGreaterThanOrEqual(4.5)
  })

  it('light mode: text1 on bgElv meets AA', () => {
    const ratio = contrastRatio(keycap.light.text1, keycap.light.bgElv)
    expect(ratio).toBeGreaterThanOrEqual(4.5)
  })

  it('accent on dark bg meets AA large text (3:1)', () => {
    // Accent is used for large text / UI elements — WCAG AA large requires 3:1
    const ratio = contrastRatio(keycap.accent, keycap.dark.bg)
    expect(ratio).toBeGreaterThanOrEqual(3.0)
  })
})

// ---------------------------------------------------------------------------
// Font string sanity
// ---------------------------------------------------------------------------

describe('keycap tokens — font stacks', () => {
  it('base font stack includes Inter', () => {
    expect(keycap.font.base).toContain('Inter')
  })

  it('mono font stack includes JetBrains Mono', () => {
    expect(keycap.font.mono).toContain('JetBrains Mono')
  })

  it('base font stack has fallback fonts', () => {
    expect(keycap.font.base.split(',')).toHaveLength(6)
  })

  it('mono font stack has fallback fonts', () => {
    expect(keycap.font.mono.split(',')).toHaveLength(4)
  })
})

describe('OS-adaptive material tokens', () => {
  it('defines the four platform groups', () => {
    expect(Object.keys(MATERIALS).sort()).toEqual(['android', 'macos', 'web', 'windows'])
  })

  it('windows material exposes mica, acrylic, and card tokens', () => {
    expect(MATERIALS.windows.base).toBe('mica')
    expect(MATERIALS.windows.acrylic).toContain('backdrop-blur(20px)')
    expect(MATERIALS.windows.card).toContain('border: 1px solid')
  })

  it('macos material exposes liquid glass tokens', () => {
    expect(MATERIALS.macos.base).toBe('liquid-glass')
    expect(MATERIALS.macos.vibrancy).toContain('backdrop-filter: blur(40px)')
    expect(MATERIALS.macos.chromaShift).toContain('rgba(126,186,181,0.3)')
  })
})

describe('stacked polygon tokens', () => {
  it('defines the expected polygon presets', () => {
    expect(Object.keys(POLYGONS).sort()).toEqual(['diamond', 'hexagon', 'pentagon', 'triangle'])
  })

  it('describes layered composite shapes', () => {
    expect(POLYGONS.hexagon.layers).toHaveLength(3)
    expect(POLYGONS.pentagon.layers).toHaveLength(4)
    expect(POLYGONS.triangle.layers.every((layer) => typeof layer.rotation === 'number')).toBe(true)
  })
})

describe('neumorphism tokens', () => {
  it('uses a top-left light source with 4px extrusion', () => {
    expect(NEUMORPHISM.lightSource).toBe('315deg')
    expect(NEUMORPHISM.extrudeDepth).toBe('4px')
  })

  it('pairs shadow and highlight offsets', () => {
    expect(NEUMORPHISM.shadow).toContain('rgba(0,0,0,0.5)')
    expect(NEUMORPHISM.shadow).toContain('rgba(126,186,181,0.1)')
    expect(NEUMORPHISM.shadowOffset).toBe('4px')
    expect(NEUMORPHISM.highlightOffset).toBe('-4px')
  })
})
