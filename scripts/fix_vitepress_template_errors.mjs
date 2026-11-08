#!/usr/bin/env node
/**
 * Compiler-oracle repair for VitePress pages whose prose contains markup the
 * Vue template compiler rejects.
 *
 * Why this exists
 * ---------------
 * VitePress compiles every Markdown page into a Vue SFC:
 *
 *     vueSrc = `<template><div>${md.render(src)}</div></template>`
 *
 * Any raw markup in prose that the Vue template compiler reads as an element
 * breaks the build with "Element is missing end tag" (or crashes the compiler
 * in `resolveComponentType`). The redaction sweep that wrote the literal token
 * `<REDACTED>` into prose was one source of this; the docs also contain
 * long-standing placeholder markup such as `<To be filled.>`, `<project>`,
 * `<family>` and `<file>`.
 *
 * How it works
 * ------------
 * The Vue compiler is used as the oracle, so only markup the compiler
 * *actually objects to* is touched:
 *
 *   1. render the page with VitePress' own markdown renderer
 *   2. compile the result as a Vue SFC template
 *   3. while the compiler complains, try escaping each unprotected `<` / `{`
 *      in the Markdown source and keep the first escape that strictly reduces
 *      the number of compiler errors
 *   4. stop when the page compiles cleanly
 *
 * Because a candidate is only accepted when the compiler gets happier,
 * intended Vue component usage, real HTML tags, fenced code blocks, inline
 * code spans, link destinations and attribute values are never rewritten:
 * they do not produce compiler errors in the first place.
 *
 * Usage
 * -----
 *     node scripts/fix_vitepress_template_errors.mjs --src-dir docs --check
 *     node scripts/fix_vitepress_template_errors.mjs --src-dir docs --apply
 */

import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { join, relative } from 'node:path'
import { createMarkdownRenderer } from 'vitepress'
import { compileTemplate } from '../docs/node_modules/@vue/compiler-sfc/dist/compiler-sfc.esm-browser.js'

const SKIP_DIRS = new Set(['node_modules', 'dist', '.git', '.vitepress', '.cache'])
const MAX_ITERATIONS = 400

// ---------------------------------------------------------------------------
// protected-region detection (a safety net: the oracle is the real authority)
// ---------------------------------------------------------------------------

function protectedMask(src) {
  const mask = new Uint8Array(src.length)

  const protect = (start, end) => {
    for (let i = start; i < end && i < mask.length; i++) mask[i] = 1
  }

  // fenced code blocks
  let offset = 0
  let fence = null
  for (const line of src.split('\n')) {
    const m = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line)
    const info = m ? m[2].trim() : ''
    if (fence === null) {
      if (m && !(m[1][0] === '`' && info.includes('`'))) {
        fence = { ch: m[1][0], len: m[1].length }
        protect(offset, offset + line.length)
      }
    } else {
      protect(offset, offset + line.length)
      if (m && m[1][0] === fence.ch && m[1].length >= fence.len && !(fence.ch === '`' && info)) {
        fence = null
      }
    }
    offset += line.length + 1
  }

  // inline code spans are NOT protected here.
  //
  // markdown-it's inline parsing is not a simple backtick pairing: a nested
  // or escaped backtick (as used heavily in the Rust error transcripts in
  // these docs) and a `|` inside a table cell both break a code span. A
  // hand-rolled mask therefore *over*-protects, hiding the very `<` the Vue
  // compiler is complaining about. Instead of guessing, the compiler itself
  // is the oracle: a `<` inside a real code span is already rendered as
  // `&lt;` by markdown-it, so it can never be the cause of a template error
  // and will never be selected.

  // html comments
  for (const m of src.matchAll(/<!--[\s\S]*?-->/g)) protect(m.index, m.index + m[0].length)

  // link destinations  ]( ... )
  //
  // markdown-it refuses to build a link for a destination whose protocol is
  // blocked (`file:`, `javascript:`, `vbscript:`, `data:`). Such a
  // destination is rendered as literal text, so a `<` inside it reaches the
  // Vue template raw and has to be escaped -- protecting it would hide the
  // very construct the compiler complains about.
  const BLOCKED_PROTO = /^\s*(javascript|vbscript|file|data):/i
  for (const m of src.matchAll(/\]\(/g)) {
    const start = m.index + m[0].length
    if (src[start] === '<') {
      const end = src.indexOf('>', start)
      if (end !== -1) protect(start, end + 1)
      continue
    }
    let depth = 1
    let k = start
    while (k < src.length && depth > 0) {
      const ch = src[k]
      if (ch === '\\') { k += 2; continue }
      if (ch === '(') depth++
      else if (ch === ')') { depth--; if (depth === 0) break }
      k++
    }
    if (!BLOCKED_PROTO.test(src.slice(start, k))) {
      protect(start, Math.min(k + 1, src.length))
    }
  }

  // html attribute values.
  //
  // The tag match is deliberately limited to a single line: an unbounded
  // `[^>]*` would happily span many lines when the source has a `<` that is
  // never closed (e.g. `/Users/<REDACTED>/Repos/`), and the "attribute"
  // it then finds could protect a large region of real prose.
  for (const m of src.matchAll(/<[A-Za-z!/?][^<>\n]*>/g)) {
    const tag = m[0]
    for (const a of tag.matchAll(/=\s*("[^"]*"|'[^']*')/g)) {
      protect(m.index + a.index, m.index + a.index + a[0].length)
    }
  }

  // <script> / <style> blocks
  for (const m of src.matchAll(/<(script|style)\b[^>]*>[\s\S]*?<\/\1\s*>/gi)) {
    protect(m.index, m.index + m[0].length)
  }

  return mask
}

// ---------------------------------------------------------------------------
// the oracle
// ---------------------------------------------------------------------------

function compileErrors(md, src, filename) {
  const env = {}
  const html = md.render(src, env)
  const vueSrc = `<template><div>${html}</div></template>`
  try {
    const res = compileTemplate({ source: vueSrc, filename, id: 'x' })
    return {
      html,
      errors: (res.errors ?? []).map((e) => String(e.message).split('\n')[0]),
    }
  } catch (e) {
    return { html, errors: [`THREW ${String(e.message).split('\n')[0]}`] }
  }
}

const VOID_TAGS = new Set(
  'area base br col embed hr img input link meta param source track wbr'.split(' '),
)

/**
 * Count element-opening tags in the rendered HTML that are never closed.
 *
 * The compiler reports only the *first* unclosed element, so "number of
 * compiler errors" is a poor progress signal: escaping one placeholder in a
 * paragraph that contains several just moves the error to the next one. The
 * unbalanced-tag count does move, so it is used as the progress signal and
 * the compiler stays the authority on whether a page is finally fixed.
 *
 * A `<` that markdown-it already escaped (inside a code span) or that sits
 * in a link destination never opens an element, so it never lowers this
 * count and is therefore never selected -- which is what keeps code spans
 * and URLs intact.
 */
function unclosedTagCount(html) {
  const stack = []
  let unmatchedEnd = 0
  const re = /<(\/?)([A-Za-z][A-Za-z0-9._:-]*)([^<>]*)>/g
  let m
  while ((m = re.exec(html)) !== null) {
    const closing = m[1] === '/'
    const name = m[2].toLowerCase()
    if (VOID_TAGS.has(name)) continue
    if (!closing && /\/\s*$/.test(m[3])) continue // self-closing
    if (closing) {
      // strict matching: an end tag must close the element that is open.
      // A lenient "pop to the matching name" would hide the defect, because
      // `</li>` would silently close a stray `<A>` element.
      if (stack.length > 0 && stack[stack.length - 1] === name) stack.pop()
      else unmatchedEnd++
    } else {
      stack.push(name)
    }
  }
  return stack.length + unmatchedEnd
}

/**
 * Score a compile result so that "the compiler crashed" always ranks worse
 * than any number of ordinary compile errors, and so that making progress on
 * a page with several unclosed elements in one paragraph is still rewarded.
 */
function errorScore(errors, html) {
  const crashed = errors.some((e) => e.startsWith('THREW '))
  return (
    (crashed ? 1e12 : 0) + errors.length * 1e6 + unclosedTagCount(html)
  )
}

/**
 * Escape a character so that it stops being markup but still renders as the
 * original character.
 *
 *   `<` -> `&lt;`   the HTML entity; markdown-it passes entities through and
 *                    the browser decodes it back to `<`
 *   `{` -> `\{`     a Markdown backslash escape; markdown-it's escape rule
 *                    emits a literal `{` and, unlike an HTML entity, the
 *                    ampersand is not double-escaped
 */
function escapeChar(ch) {
  return ch === '<' ? '&lt;' : '\\{'
}

/**
 * Positions in the source that could be markup the Vue compiler objects to.
 *
 * `<` is always a candidate. `{` is a candidate when it opens a Vue
 * interpolation (`{{ ... }}`) or a markdown-it-attrs attribute block
 * (`{ ... }` at the end of a line) -- VitePress enables markdown-it-attrs, so
 * a Rust-looking `{ fn f(&self) -> String; }` is parsed as element attributes
 * and ends up as a broken `<li fn=...>`.
 */
function candidatePositions(src, mask) {
  const out = []
  for (let i = 0; i < src.length; i++) {
    const ch = src[i]
    if (ch !== '<' && ch !== '{') continue
    if (mask[i]) continue
    if (ch === '{') {
      // markdown-it-attrs: `{ ... }` as the last thing on the line.
      //
      // A Vue interpolation `{{ ... }}` is deliberately NOT a candidate: a
      // Markdown backslash escape is unescaped again by markdown-it, so the
      // rendered HTML would still contain `{{` and Vue would still try to
      // compile it. Interpolations are handled by the `v-pre` fallback.
      const lineEnd = src.indexOf('\n', i)
      const line = src.slice(i, lineEnd === -1 ? src.length : lineEnd)
      if (!/^\{[^}\n]*\}\s*$/.test(line)) continue
    }
    out.push(i)
  }
  return out
}

/**
 * HTML tags the Vue compiler understands natively. Anything else is read as a
 * component/element and therefore has to be closed, which is what breaks the
 * build when a doc contains a placeholder such as `<To be filled.>`.
 */
const HTML_TAGS = new Set(
  ('a abbr address area article aside audio b base bdi bdo blockquote body br button canvas caption cite code col colgroup ' +
    'data datalist dd del details dfn dialog div dl dt em embed fieldset figcaption figure footer form h1 h2 h3 h4 h5 h6 head ' +
    'header hr html i iframe img input ins kbd label legend li link main map mark menu meta meter nav noscript object ol ' +
    'optgroup option output p param picture pre progress q rp rt ruby s samp script section select slot small source span ' +
    'strong style sub summary sup table tbody td template textarea tfoot th thead time title tr track u ul var video wbr ' +
    'svg path g circle rect line polyline polygon text defs use symbol marker lineargradient stop')
    .split(' '),
)

/**
 * Escape every unprotected `<` that starts something the Vue compiler would
 * read as an element: a name that is not a native HTML tag, that is not
 * self-closing, and that has no matching end tag later in the file.
 *
 * This is the bulk fallback for pages where several placeholders sit in the
 * same paragraph: escaping them one at a time only moves the compiler error
 * to the next placeholder instead of removing it, so a "strictly fewer
 * errors" search stalls. The result is still validated by the compiler
 * before it is accepted.
 */
function bulkProseEscapes(src, mask) {
  let out = ''
  let last = 0
  let count = 0
  for (let i = 0; i < src.length; i++) {
    if (src[i] !== '<' || mask[i]) continue
    const m = /^<([A-Za-z][A-Za-z0-9._:-]*)/.exec(src.slice(i))
    if (!m) continue
    const name = m[1].toLowerCase()
    if (HTML_TAGS.has(name)) continue
    const after = src.slice(i + 1 + m[1].length)
    if (/^\s*\/>/.test(after)) continue // self-closing component
    if (src.toLowerCase().includes(`</${name.toLowerCase()}>`)) continue // has a real end tag
    out += src.slice(last, i) + '&lt;'
    last = i + 1
    count++
  }
  out += src.slice(last)
  return { text: out, count }
}

/**
 * Wrap a page body in `<div v-pre>` so the Vue template compiler skips
 * interpolation for the whole page.
 *
 * This is the only repair for a page whose *text* contains `{{ ... }}`
 * (shell templates such as `docker inspect --format '{{.Config.Image}}'`).
 * Escaping the braces cannot work: markdown-it escapes `&` inside code spans
 * and inside text, so `&#123;` would render literally. `v-pre` disables
 * interpolation for the subtree while leaving the text untouched.
 *
 * YAML frontmatter is kept outside the wrapper so it stays frontmatter.
 */
function wrapInVPre(src) {
  let body = src
  let prefix = ''
  if (src.startsWith('---')) {
    const end = src.indexOf('\n---', 3)
    if (end !== -1) {
      const after = src.indexOf('\n', end + 1)
      if (after !== -1) {
        prefix = src.slice(0, after + 1)
        body = src.slice(after + 1)
      }
    }
  }
  return `${prefix}<div v-pre>\n${body}\n</div>\n`
}

// ---------------------------------------------------------------------------
// driver
// ---------------------------------------------------------------------------

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    if (SKIP_DIRS.has(name)) continue
    const p = join(dir, name)
    let st
    try {
      st = statSync(p)
    } catch {
      continue
    }
    if (st.isDirectory()) walk(p, out)
    else if (name.endsWith('.md')) out.push(p)
  }
  return out
}

async function main() {
  const argv = process.argv.slice(2)
  const getArg = (name, fallback) => {
    const i = argv.indexOf(name)
    return i === -1 ? fallback : argv[i + 1]
  }
  const srcDir = getArg('--src-dir', 'docs')
  const only = getArg('--file', null)
  const apply = argv.includes('--apply')
  const check = argv.includes('--check')
  if (!apply && !check) {
    console.error('choose --check or --apply')
    process.exit(2)
  }

  const md = await createMarkdownRenderer(srcDir, {}, '/')
  const files = only ? [only] : walk(srcDir)
  console.log(`src-dir: ${srcDir}   markdown files: ${files.length}`)

  const changed = []
  const unfixable = []
  let totalEscapes = 0

  for (const file of files) {
    let src
    try {
      src = readFileSync(file, 'utf8')
    } catch {
      continue
    }
    let { html, errors } = compileErrors(md, src, file)
    if (!errors.length) continue

    const mask = protectedMask(src)
    let candidates = candidatePositions(src, mask)
    let escapes = 0
    let current = src
    let score = errorScore(errors, html)

    while (errors.length && escapes < MAX_ITERATIONS) {
      let best = null
      let bestErrors = null
      let bestHtml = null
      for (const pos of candidates) {
        if (pos > current.length) continue
        const ch = current[pos]
        if (ch !== '<' && ch !== '{') continue
        const variant =
          current.slice(0, pos) + escapeChar(ch) + current.slice(pos + 1)
        const r = compileErrors(md, variant, file)
        if (errorScore(r.errors, r.html) < score) {
          best = variant
          bestErrors = r.errors
          bestHtml = r.html
          break
        }
      }
      if (best === null) {
        // fallback A: escape every placeholder-ish '<' in prose at once.
        // Escaping them one at a time only moves the compiler error to the
        // next placeholder, so the "strictly fewer errors" search stalls.
        const bulk = bulkProseEscapes(current, protectedMask(current))
        if (bulk.count > 0) {
          const r = compileErrors(md, bulk.text, file)
          if (errorScore(r.errors, r.html) < score) {
            best = bulk.text
            bestErrors = r.errors
            bestHtml = r.html
          }
        }
      }
      if (best === null) {
        // fallback B: a page whose *text* contains `{{ ... }}` cannot be fixed
        // by escaping characters; disable interpolation for the page instead
        const variant = wrapInVPre(current)
        const r = compileErrors(md, variant, file)
        if (errorScore(r.errors, r.html) < score) {
          best = variant
          bestErrors = r.errors
          bestHtml = r.html
        }
      }
      if (best === null) break
      current = best
      errors = bestErrors
      html = bestHtml
      score = errorScore(errors, html)
      escapes++
      // an escape changes the string length, so candidate offsets must be
      // recomputed against the new source
      const newMask = protectedMask(current)
      candidates = candidatePositions(current, newMask)
    }

    if (escapes > 0 && errors.length === 0) {
      changed.push({ file, escapes })
      totalEscapes += escapes
      if (apply) writeFileSync(file, current, 'utf8')
    } else {
      unfixable.push({ file, escapes, errors: errors.slice(0, 2) })
    }
  }

  console.log(`\nmode: ${apply ? 'apply' : 'check'}`)
  console.log(`pages repaired  : ${changed.length}`)
  console.log(`escapes applied : ${totalEscapes}`)
  console.log(`pages unfixable : ${unfixable.length}`)
  for (const u of unfixable) {
    console.log(`  UNFIXABLE ${u.file}  (${u.escapes} escapes, ${JSON.stringify(u.errors)})`)
  }
  const byEscapes = [...changed].sort((a, b) => b.escapes - a.escapes)
  console.log('\nper-page escape counts (top 20):')
  for (const c of byEscapes.slice(0, 20)) {
    console.log(`  ${String(c.escapes).padStart(3)}  ${relative(process.cwd(), c.file)}`)
  }
  writeFileSync(
    process.env.VITEPRESS_FIX_REPORT || '/dev/null',
    JSON.stringify({ changed, unfixable, totalEscapes }, null, 2),
  )
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
