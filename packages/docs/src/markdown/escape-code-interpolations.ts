/**
 * Escape Vue interpolations that appear inside rendered code samples.
 *
 * Why this is needed
 * ------------------
 * VitePress compiles every Markdown page into a Vue SFC:
 *
 *     vueSrc = `<template><div>${md.render(src)}</div></template>`
 *
 * The Vue template compiler scans the whole template for `{{ ... }}`, so a
 * code sample that contains `{{` -- an Askama/Jinja template, a Rust
 * `format!` placeholder, a shell `--format '{{.Config.Image}}'` flag -- is
 * compiled as a Vue interpolation. At SSR time the referenced variable does
 * not exist and the build dies with:
 *
 *     Cannot read properties of undefined (reading 'as_deref')
 *
 * Replacing the two opening braces with the HTML entity `&#123;` keeps the
 * rendered text identical (the browser decodes the entity back to `{`) while
 * hiding the interpolation from the Vue compiler. Only code samples are
 * rewritten: prose that legitimately uses `{{ }}` keeps working.
 */

/** Minimal structural type so this helper needs no extra dependency. */
interface MarkdownItLike {
  renderer: {
    rules: Record<
      string,
      | ((tokens: unknown[], idx: number, options: unknown, env: unknown, self: unknown) => string)
      | undefined
    >
  }
}

const CODE_RULES = ['code_inline', 'code_block', 'fence'] as const

export function escapeCodeInterpolations(md: MarkdownItLike): void {
  const escape = (html: string): string => html.replace(/\{\{/g, '&#123;&#123;')

  for (const rule of CODE_RULES) {
    const original = md.renderer.rules[rule]
    if (!original) continue
    md.renderer.rules[rule] = (tokens, idx, options, env, self) =>
      escape(original(tokens, idx, options, env, self))
  }
}
