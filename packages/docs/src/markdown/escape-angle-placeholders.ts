/**
 * Escape angle-bracket *placeholders* so the Vue template compiler never sees
 * them as unclosed HTML elements.
 *
 * Why this is needed
 * ------------------
 * VitePress compiles every Markdown page into a Vue SFC:
 *
 *     vueSrc = `<template><div>${md.render(src)}</div></template>`
 *
 * The Vue template compiler parses that string as HTML. Absorbed documents in
 * this tree are verbatim captures of audited repos and use bare angle-bracket
 * placeholders in prose and tables:
 *
 *     > **Audit baseline:** <REDACTED>/substrate @ ...
 *     | <capability or interface> | <green|amber|red> |
 *     `Future<Output = Result<T, Error>>`
 *     <repo>  <this-repo>  <YYYY-MM-DD>  <WPID>
 *
 * With `html: true`, markdown-it hands `<REDACTED>`, `<T>`, `<repo>`,
 * `<String>` ... to Vue as opening tags with no end tag, and the build dies:
 *
 *     [plugin vite:vue] absorbed-root-docs/....md (6:37): Element is missing end tag.
 *
 * Rewriting ~2,000 placeholders across 424 absorbed documents would churn the
 * port diff and destroy verbatim captures, so the fix belongs in the Markdown
 * pipeline. Escaping only the `<` (to `&lt;`) keeps the rendered text identical
 * (browsers decode the entity back to `<`) while hiding the tag from Vue.
 *
 * What is preserved
 * -----------------
 * - Real HTML tags (`<div>`, `<details>`, `<summary>`, `<img ...>`, `<br>`,
 *   `<table>`, `<td>`, `<a href>` ...) are matched against an allowlist of
 *   HTML/SVG element names and left untouched.
 * - Self-closing components used by real pages (`<CategorySwitcher />`,
 *   `<TestCoverageBadge :overall="90" />`) are left untouched.
 * - Paired components (`<Dashboard>...</Dashboard>`) are left untouched: the
 *   document is pre-scanned for explicit end tags and those names are kept.
 * - Code spans, fenced code blocks and autolinks are never visited: this
 *   plugin rewrites tokens, and those live in `code_inline` / `code_block` /
 *   `fence` / `link` tokens, not in `text` / `html_*` tokens.
 */

/** Minimal structural types so this helper needs no extra dependency. */
interface MarkdownToken {
  type: string
  content: string
  children?: MarkdownToken[] | null
}

interface MarkdownItLike {
  core: { ruler: { after: (afterName: string, ruleName: string, fn: (state: { tokens: MarkdownToken[] }) => void) => void } }
}

/**
 * Element names that are genuine HTML/SVG and must keep working.
 * Lowercase because HTML tag names are case-insensitive.
 */
const HTML_TAGS = new Set([
  // document / metadata
  'html', 'head', 'body', 'title', 'base', 'link', 'meta', 'style', 'script',
  'noscript', 'template', 'slot',
  // sections
  'address', 'article', 'aside', 'footer', 'header', 'h1', 'h2', 'h3', 'h4',
  'h5', 'h6', 'hgroup', 'main', 'nav', 'section', 'search',
  // grouping
  'blockquote', 'div', 'dl', 'dt', 'dd', 'figure', 'figcaption', 'hr', 'li',
  'menu', 'ol', 'p', 'pre', 'ul',
  // text-level
  'a', 'abbr', 'b', 'bdi', 'bdo', 'br', 'cite', 'code', 'data', 'dfn', 'em',
  'i', 'kbd', 'mark', 'q', 'rp', 'rt', 'ruby', 's', 'samp', 'small', 'span',
  'strong', 'sub', 'sup', 'time', 'u', 'var', 'wbr', 'ins', 'del',
  // media / embeds
  'area', 'audio', 'canvas', 'embed', 'iframe', 'img', 'map', 'object',
  'param', 'picture', 'portal', 'source', 'track', 'video',
  // tables
  'caption', 'col', 'colgroup', 'table', 'tbody', 'td', 'tfoot', 'th',
  'thead', 'tr',
  // forms
  'button', 'datalist', 'fieldset', 'form', 'input', 'label', 'legend',
  'meter', 'optgroup', 'option', 'output', 'progress', 'select', 'textarea',
  // interactive
  'details', 'summary', 'dialog',
  // SVG
  'svg', 'g', 'defs', 'symbol', 'use', 'path', 'circle', 'ellipse', 'line',
  'polygon', 'polyline', 'rect', 'text', 'tspan', 'textpath', 'marker',
  'pattern', 'mask', 'clippath', 'lineargradient', 'radialgradient', 'stop',
  'filter', 'fegaussianblur', 'feoffset', 'femerge', 'feblend', 'image',
  // Vue built-ins
  'component', 'transition', 'transitiongroup', 'keepalive', 'teleport',
  'suspense',
])

/**
 * Matches one angle-bracket construct: optional closing slash, tag name,
 * optional attribute text, then `>`.
 *
 *   <REDACTED>            name only
 *   <capability or x>     name + words (attribute text)
 *   <green|amber|red>     name + pipe text
 *   <CategorySwitcher />  self-closing
 *   </div>                closing
 */
const TAG_RE = /<(\/?)([A-Za-z][A-Za-z0-9_.:-]*)([^<>]*)>/g
const END_TAG_RE = /<\/([A-Za-z][A-Za-z0-9_.:-]*)\s*>/g

function escapePlaceholderTag(
  match: string,
  closingSlash: string,
  name: string,
  attributes: string,
  pairedComponents: Set<string>
): string {
  // Genuine HTML / SVG element -> leave both opening and closing tags alone.
  if (HTML_TAGS.has(name.toLowerCase())) return match

  // Self-closing component (`<Foo />`, `<ProductInfo product={p} />`) -> leave.
  if (!closingSlash && /\/\s*$/.test(attributes)) return match

  // A name that this document explicitly closes (`<Dashboard>...</Dashboard>`)
  // is a real component -> leave both halves alone so the pair stays matched.
  if (pairedComponents.has(name)) return match

  // Everything else is a placeholder: escape only the `<`.
  return `&lt;${closingSlash}${name}${attributes}>`
}

/** Names an explicit `</Name>` appears for anywhere in the document. */
function collectPairedComponents(tokens: MarkdownToken[], into: Set<string>): void {
  for (const token of tokens) {
    if (token.children) collectPairedComponents(token.children, into)

    if (
      (token.type === 'html_inline' || token.type === 'html_block' || token.type === 'text') &&
      typeof token.content === 'string' &&
      token.content.includes('</')
    ) {
      for (const found of token.content.matchAll(END_TAG_RE)) into.add(found[1])
    }
  }
}

function escapeTokens(tokens: MarkdownToken[], pairedComponents: Set<string>): void {
  for (const token of tokens) {
    if (token.children) escapeTokens(token.children, pairedComponents)

    if (
      token.type === 'text' ||
      token.type === 'html_inline' ||
      token.type === 'html_block'
    ) {
      if (typeof token.content === 'string' && token.content.includes('<')) {
        token.content = token.content.replace(TAG_RE, (match, closingSlash, name, attributes) =>
          escapePlaceholderTag(match, closingSlash, name, attributes, pairedComponents)
        )
      }
    }
  }
}

export function escapeAnglePlaceholders(md: MarkdownItLike): void {
  md.core.ruler.after('inline', 'escape_angle_placeholders', (state) => {
    const pairedComponents = new Set<string>()
    collectPairedComponents(state.tokens, pairedComponents)
    escapeTokens(state.tokens, pairedComponents)
  })
}
