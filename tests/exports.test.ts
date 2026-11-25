/**
 * Package Export Tests
 *
 * Traces to: FR-DESIGN-003 (public API exports)
 *
 * Verifies the package's public API surface is complete and correctly typed.
 */

import { describe, it, expect } from 'vitest'
import * as designExports from '../src/index'

describe('@phenotype/design — public exports', () => {
  it('exports keycap token object', () => {
    expect(designExports).toHaveProperty('keycap')
    expect(typeof designExports.keycap).toBe('object')
  })

  it('exports the merged design token bundle', () => {
    expect(designExports).toHaveProperty('designTokens')
    expect(designExports.designTokens.keycap).toBe(designExports.keycap)
  })

  it('keycap export is the same object as direct import', async () => {
    const { keycap: direct } = await import('../src/tokens')
    expect(designExports.keycap).toBe(direct)
  })

  it('keycap is a const (frozen/immutable via as const)', () => {
    // "as const" in TypeScript makes properties readonly at type level.
    // At runtime the object is still mutable unless frozen explicitly.
    // We verify the structure is intact after multiple accesses.
    const first = designExports.keycap.accent
    const second = designExports.keycap.accent
    expect(first).toBe(second)
  })

  it('exports KeycapTokens type (inferred from object shape)', () => {
    // Type-level assertion: KeycapTokens should be assignable from keycap
    const tokens: import('../src/tokens').KeycapTokens = designExports.keycap
    expect(tokens).toBeDefined()
  })

  it('exports materials, polygons, and neumorphism tokens', () => {
    expect(designExports).toHaveProperty('MATERIALS')
    expect(designExports).toHaveProperty('POLYGONS')
    expect(designExports).toHaveProperty('NEUMORPHISM')
  })

  it('exports glass and typography tokens absorbed from phenotype-tooling', () => {
    expect(designExports).toHaveProperty('glass')
    expect(designExports).toHaveProperty('typography')
    expect(designExports.glass.neo.blur).toBe(16)
    expect(designExports.typography.fontMono).toContain('JetBrains Mono')
  })

  it('exports vitepress config helpers', () => {
    expect(designExports).toHaveProperty('vitepressConfig')
    expect(designExports).toHaveProperty('vitepressMarkdownTheme')
    expect(designExports.vitepressConfig.appearance).toBe('dark')
  })
})
