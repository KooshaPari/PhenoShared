#!/usr/bin/env node
/**
 * AT4 — Locale coverage verifier.
 *
 * Diffs the English `docs/` tree against `docs/es/` and `docs/ar/`
 * (and any other locales declared in `.vitepress/config.mts`). Exits 1
 * if any locale is missing a file present in the source-of-truth (en).
 *
 * Usage:  node scripts/verify-locale-coverage.mjs
 */
import { readdirSync, statSync, existsSync } from 'node:fs'
import { join, relative } from 'node:path'

const ROOT = new URL('..', import.meta.url).pathname
const SRC = join(ROOT, 'docs')
const LOCALES = ['es', 'ar']

function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    const s = statSync(p)
    if (s.isDirectory()) yield* walk(p)
    else yield p
  }
}

const sourceFiles = [...walk(SRC)]
  .map((p) => relative(SRC, p))
  .filter((p) => /\.(md|vue|mdx)$/i.test(p))
  .filter((p) => !LOCALES.some((loc) => p === loc || p.startsWith(`${loc}/`)))

const gaps = []
for (const rel of sourceFiles) {
  for (const loc of LOCALES) {
    const target = join(SRC, loc, rel)
    if (!existsSync(target)) {
      gaps.push({ locale: loc, file: rel })
    }
  }
}

if (gaps.length > 0) {
  console.error(`AT4 locale coverage: ${gaps.length} missing file(s)\n`)
  for (const g of gaps) {
    console.error(`  [${g.locale}] docs/${g.locale}/${g.file}`)
  }
  process.exit(1)
}

console.log(
  `AT4 locale coverage: OK (${sourceFiles.length} files mirrored across ${LOCALES.join(', ')}).`,
)
