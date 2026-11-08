# VitePress docs build: `<REDACTED>` escaping

**Date:** 2026-11-07
**Branch:** `fix/vitepress-redacted-escaping`
**Status:** build green (see Verification)

## Problem

`bun run build` (root VitePress site, `srcDir: 'docs'`) and `cd docs && bun run
docs:build` (CI-gated Pages build, `srcDir: '.'`) both failed:

```
[vite:vue] [plugin vite:vue] docs/.../DOSSIER.md (4:40): Element is missing end tag.
```

VitePress compiles every Markdown page into a Vue SFC
(`<template><div>${md.render(src)}</div></template>`), so a raw `<REDACTED>` in
prose is read by the Vue template compiler as an unclosed HTML element.

## Root causes (five, all distinct)

| # | Cause | Scope | Fix |
|---|-------|-------|-----|
| 1 | Redaction sweep wrote the literal token `<REDACTED>` into prose | 167 files, 338 occurrences | `scripts/escape_redacted_for_vitepress.py` |
| 2 | Long-standing placeholder markup in prose (`<To be filled.>`, `<project>`, `<Vec<T>>`, …) | 258 files, 591 occurrences | `scripts/fix_vitepress_template_errors.mjs` |
| 3 | Dead `<script setup>` importing two Vue components that do not exist anywhere in the repo | 1 file | removed the unused import block |
| 4 | `{{ … }}` inside code samples compiled as Vue interpolations → SSR crash (`Cannot read properties of undefined (reading 'as_deref')`) | 40 pages, 400 occurrences | `packages/docs/src/markdown/escape-code-interpolations.ts` |
| 5 | Node's default V8 heap (~1.5 GB) is not enough to compile and SSR-render 2566 pages | build | explicit `--max-old-space-size=8192` in the build scripts |

Causes 2–4 were masked by cause 1: the compiler aborts on the first error, so
each build only ever surfaced one file at a time.

## Scripts

### `scripts/escape_redacted_for_vitepress.py`

Escapes the literal token `<REDACTED>` → `&lt;REDACTED&gt;` in prose only.
Fenced code blocks, inline code spans, link/image destinations, reference
definitions, Vue interpolations, `<script>`/`<style>` blocks, HTML attribute
values and HTML comments are left alone — markdown-it already escapes the
first group, and escaping the others would corrupt URLs or rendered text.

Idempotent: `&lt;REDACTED&gt;` never contains the literal token.

### `scripts/fix_vitepress_template_errors.mjs`

Compiler-oracle repair for cause 2. For every page it renders the Markdown
with VitePress' own renderer, compiles the result as a Vue SFC template (the
same thing `@vitejs/plugin-vue` does), and escapes only the `<` / `{` that the
compiler actually objects to. A candidate is accepted only when the compiler
gets strictly better, so intended component usage, real HTML tags, code
samples and URLs are never rewritten.

Progress is measured by the number of unbalanced tags in the rendered HTML,
because the compiler reports only the *first* unclosed element — escaping one
placeholder in a paragraph that holds several just moves the error to the
next one.

## Verification

* `scripts/tests/test_escape_redacted_for_vitepress.py` — 24 unit checks.
* Per-page compile check over all 2566 pages under `docs/`: 0 failures.
* `cd docs && bun run docs:build` → exit 0, `build complete in 15757.63s`
  (the wall clock reflects a load average of 35–75 from concurrent builds on
  the host; an idle run of the same tree completed in 203s).
* `bun run build` → exit 0, `build complete in 227.47s`.

## Known limitations

* The `<REDACTED>` token remains a literal in code spans, link destinations
  and reference definitions. That is deliberate: markdown-it already escapes
  code spans, and escaping a URL would change it (`&lt;` → `%26lt%3B`).
* Pages whose prose contains `{{ … }}` legitimately (outside code samples)
  still compile as Vue interpolations. Only code samples are rewritten.
* The local `node_modules/` was missing a hoisted `@vueuse/core` (a vitepress
  dependency); a symlink into the existing local store was created. That is a
  local install repair, not a repository change.
