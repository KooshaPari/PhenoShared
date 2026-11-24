#!/usr/bin/env node
/**
 * AT3 — Image alt-text checker.
 *
 * Walks `docs/**\/*.md` (and any `.vue` files) and asserts that every
 * `<img>` tag (whether authored as markdown `![alt](src)` or raw HTML
 * in MDX) has a non-empty `alt` attribute. Exits 1 on the first miss.
 *
 * Usage:  node scripts/check-image-alts.mjs
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const ROOT = new URL('..', import.meta.url).pathname
const SRC = join(ROOT, 'docs')

const offenders = []

function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    const p = join(dir, entry)
    const s = statSync(p)
    if (s.isDirectory()) yield* walk(p)
    else yield p
  }
}

function check(file) {
  const text = readFileSync(file, 'utf8')
  const lines = text.split('\n')

  // 1. Markdown: ![alt](src) — alt must be non-empty.
  const mdRe = /!\[([^\]]*)\]\([^)]+\)/g
  for (let i = 0; i < lines.length; i++) {
    let m
    while ((m = mdRe.exec(lines[i])) !== null) {
      if (m[1].trim() === '') {
        offenders.push({ file, line: i + 1, kind: 'markdown', msg: 'empty alt text' })
      }
    }
  }

  // 2. HTML: <img ...> — must have alt attribute (any value, including '' for decorative).
  const imgRe = /<img\b([^>]*)>/gi
  for (let i = 0; i < lines.length; i++) {
    let m
    while ((m = imgRe.exec(lines[i])) !== null) {
      if (!/\balt\s*=/i.test(m[1])) {
        offenders.push({
          file,
          line: i + 1,
          kind: 'html-img',
          msg: '<img> missing alt attribute (use alt="" for decorative)',
        })
      }
    }
  }
}

for (const p of walk(SRC)) {
  if (/\.(md|vue|mdx)$/i.test(p)) check(p)
}

if (offenders.length > 0) {
  console.error(`AT3 alt-text check failed: ${offenders.length} issue(s)\n`)
  for (const o of offenders) {
    console.error(`  ${relative(ROOT, o.file)}:${o.line}  [${o.kind}] ${o.msg}`)
  }
  process.exit(1)
}

console.log('AT3 alt-text check: OK (no missing alts).')
