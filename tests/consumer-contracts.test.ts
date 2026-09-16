/**
 * Consumer Contract Tests — `@phenotype/design`
 *
 * Traces to: CONSUMERS.md (2026-09-08 audit), audit/2026-09-05 R2/phenoDesign.
 *
 * The existing `exports.test.ts` and `tokens.test.ts` lock the in-package
 * shape (what the package itself exports). This file locks the
 * **consumer-side contract** — the symbols and assets that real downstream
 * packages (phenodocs root, phenodocs/packages/docs) actually import today.
 *
 * The audit explicitly excluded authority transfer ("no migration, no
 * absorption"), so these tests are deliberately conservative: they pin
 * what is currently consumed, so that a future rename or removal in
 * `@phenotype/design` fails CI here before it breaks a downstream
 * VitePress site at runtime.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync, existsSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { fileURLToPath } from 'node:url'

// Resolve the package root from this test file's location so the tests
// work whether invoked from `bun run test`, `vitest run`, or the
// standalone `tests/` directory. `../../` from `tests/<file>.ts` lands
// in the package root.
const __filename = fileURLToPath(import.meta.url)
const __dirname = resolve(__filename, '..')
const PACKAGE_ROOT = resolve(__dirname, '..')

// ---------------------------------------------------------------------------
// CSS asset paths consumers import
// ---------------------------------------------------------------------------

describe('@phenotype/design — CSS asset contracts (consumer-facing)', () => {
  // phenodocs/phenodocs and phenodocs/phenodocs/packages/docs both do:
  //   @import '@phenotype/design/css/vitepress-theme.css';
  // (See CONSUMERS.md §2.) If this file disappears or stops importing
  // its dependencies, every Phenotype VitePress site silently loses
  // its theme.

  it('css/vitepress-theme.css exists at the export path', () => {
    const p = join(PACKAGE_ROOT, 'css', 'vitepress-theme.css')
    expect(existsSync(p)).toBe(true)
  })

  it('css/keycap-palette.css exists at the export path', () => {
    const p = join(PACKAGE_ROOT, 'css', 'keycap-palette.css')
    expect(existsSync(p)).toBe(true)
  })

  it('css/components.css exists at the export path', () => {
    const p = join(PACKAGE_ROOT, 'css', 'components.css')
    expect(existsSync(p)).toBe(true)
  })

  it('css/glass.css exists at the export path', () => {
    const p = join(PACKAGE_ROOT, 'css', 'glass.css')
    expect(existsSync(p)).toBe(true)
  })

  it('vitepress-theme.css @imports both palette and components (consumer relies on the cascade)', () => {
    const src = readFileSync(
      join(PACKAGE_ROOT, 'css', 'vitepress-theme.css'),
      'utf8',
    )
    // The consumer imports ONE file; that file must chain-load the
    // other two or the theme is incomplete. Drift here means a
    // silent visual regression at every consumer site.
    expect(src).toMatch(/@import\s+['"]\.\/keycap-palette\.css['"]/)
    expect(src).toMatch(/@import\s+['"]\.\/components\.css['"]/)
  })

  it('vitepress-theme.css declares the brand color consumers key off', () => {
    // phenodocs/custom.css expects --vp-c-brand-* to render teal.
    // If the brand triple drifts, every CTA in the VitePress UI
    // changes color without any consumer-side test catching it.
    const src = readFileSync(
      join(PACKAGE_ROOT, 'css', 'vitepress-theme.css'),
      'utf8',
    )
    expect(src).toMatch(/--vp-c-brand-1:\s*#7ebab5/)
    expect(src).toMatch(/--vp-c-brand-2:\s*#6aa8a3/)
    expect(src).toMatch(/--vp-c-brand-3:\s*#569691/)
  })

  it('keycap-palette.css defines the CSS custom properties the theme references', () => {
    const src = readFileSync(
      join(PACKAGE_ROOT, 'css', 'keycap-palette.css'),
      'utf8',
    )
    // --kc-* tokens are what vitepress-theme.css maps to --vp-c-*.
    // If any of these names change, the theme silently breaks.
    for (const token of [
      '--kc-accent',
      '--kc-bg',
      '--kc-bg-alt',
      '--kc-bg-soft',
      '--kc-bg-elv',
      '--kc-text-1',
      '--kc-text-2',
      '--kc-text-3',
      '--kc-divider',
      '--kc-gutter',
      '--kc-font-base',
      '--kc-font-mono',
    ]) {
      expect(src).toContain(token)
    }
  })
})

// ---------------------------------------------------------------------------
// package.json exports contract — what the npm-name-resolver exposes
// ---------------------------------------------------------------------------

describe('@phenotype/design — package.json exports contract', () => {
  const pkg = JSON.parse(
    readFileSync(join(PACKAGE_ROOT, 'package.json'), 'utf8'),
  ) as {
    name: string
    version: string
    exports: Record<string, unknown>
    files: string[]
  }

  it('keeps the canonical package name `@phenotype/design`', () => {
    // Both phenodocs consumers pin this exact name. A rename
    // requires a coordinated migration; this test makes the
    // rename visible at CI time.
    expect(pkg.name).toBe('@phenotype/design')
  })

  it('declares every CSS asset path consumers import', () => {
    const exp = pkg.exports as Record<string, unknown>
    for (const subpath of [
      './css/vitepress-theme.css',
      './css/keycap-palette.css',
      './css/components.css',
      './css/glass.css',
    ]) {
      expect(exp).toHaveProperty(subpath)
    }
  })

  it('declares the root `.` export (consumers may add it later)', () => {
    const exp = pkg.exports as Record<string, unknown>
    expect(exp).toHaveProperty('.')
  })

  it('publishes the css/ directory so consumers actually receive it', () => {
    // exports alone is not enough — if `files` omits `css/`, npm
    // will ship an empty package.
    expect(pkg.files).toContain('css/')
  })
})

// ---------------------------------------------------------------------------
// Token JSON contract — what W3C DTCG consumers parse
// ---------------------------------------------------------------------------

describe('@phenotype/design — W3C DTCG token JSON contract', () => {
  // packages/design-tokens ships tokens.css; tokens/keycap.json is the
  // DTCG-format single source of truth. Future tooling (Style
  // Dictionary, terrazzo) parses this file. A schema drift here
  // breaks every external token consumer silently.

  it('keycap.json exists and references the DTCG community schema', () => {
    const p = join(PACKAGE_ROOT, 'tokens', 'keycap.json')
    expect(existsSync(p)).toBe(true)
    const json = JSON.parse(readFileSync(p, 'utf8')) as { $schema?: string }
    expect(json.$schema).toContain('design-tokens.github.io/community-group/format')
  })

  it('keycap.json declares the canonical accent color consumers key off', () => {
    const json = JSON.parse(
      readFileSync(join(PACKAGE_ROOT, 'tokens', 'keycap.json'), 'utf8'),
    ) as {
      keycap?: {
        color?: {
          accent?: { $value?: string }
        }
      }
    }
    // The TS bundle (keycap.ts) and the DTCG JSON (keycap.json) must
    // agree on accent — drift here means consumers reading one source
    // see a different color than consumers reading the other.
    expect(json.keycap?.color?.accent?.$value).toBe('#7ebab5')
  })
})
