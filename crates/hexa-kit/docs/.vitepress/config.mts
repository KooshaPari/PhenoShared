import { withMermaid } from 'vitepress-plugin-mermaid'
import type { DefaultTheme } from 'vitepress'

const htmlInlineTags = new Set([
  'a',
  'abbr',
  'b',
  'br',
  'button',
  'code',
  'details',
  'div',
  'em',
  'i',
  'img',
  'kbd',
  'li',
  'ol',
  'p',
  'pre',
  'span',
  'strong',
  'summary',
  'sup',
  'table',
  'tbody',
  'td',
  'th',
  'thead',
  'tr',
  'ul',
])

const placeholderAngleToken = /<([^<>\n]+)>/g

function escapePlaceholderAngles(content: string): string {
  return content.replace(placeholderAngleToken, (match, inner: string) => {
    const trimmed = inner.trim()
    const tagName = trimmed.split(/[\s=]/, 1)[0].toLowerCase()

    if (trimmed.startsWith('!--') || trimmed.startsWith('/')) {
      return match
    }

    if (trimmed === tagName && htmlInlineTags.has(tagName)) {
      return match
    }

    if (htmlInlineTags.has(tagName) && /^[a-z][a-z0-9-]*(\s|$)/.test(trimmed)) {
      return match
    }

    return `&lt;${inner}&gt;`
  })
}

const referenceSidebar: DefaultTheme.SidebarItem[] = [
  {
    text: 'Reference',
    items: [
      { text: 'Traceability map', link: '/reference/TRACEABILITY_MAP' },
      { text: 'Configuration standards', link: '/reference/CONFIGURATION_STANDARDS' },
      { text: 'Validation standards', link: '/reference/VALIDATION_STANDARDS' },
      { text: 'FR tracker', link: '/reference/FR_TRACKER' },
    ],
  },
]

const adoptionSidebar: DefaultTheme.SidebarItem[] = [
  {
    text: 'Crate adoption',
    items: [
      { text: 'Overview', link: '/adoption/' },
      { text: 'phenotype-config-core', link: '/adoption/phenotype-config-core' },
      { text: 'phenotype-crypto', link: '/adoption/phenotype-crypto' },
      { text: 'phenotype-error-core', link: '/adoption/phenotype-error-core' },
      { text: 'phenotype-health', link: '/adoption/phenotype-health' },
      { text: 'phenotype-iter', link: '/adoption/phenotype-iter' },
      { text: 'phenotype-logging', link: '/adoption/phenotype-logging' },
      { text: 'phenotype-port-traits', link: '/adoption/phenotype-port-traits' },
      { text: 'phenotype-retry', link: '/adoption/phenotype-retry' },
      { text: 'phenotype-string', link: '/adoption/phenotype-string' },
      { text: 'phenotype-time', link: '/adoption/phenotype-time' },
    ],
  },
]

const overviewSidebar: DefaultTheme.SidebarItem[] = [
  {
    text: 'Overview',
    items: [
      { text: 'Home', link: '/' },
      { text: 'Architecture', link: '/architecture' },
      { text: 'Defensive patterns', link: '/DEFENSIVE_PATTERNS' },
      { text: 'LOC reduction', link: '/LOC_REDUCTION_OPPORTUNITIES' },
    ],
  },
  {
    text: 'Sections',
    items: [
      { text: 'Guide', link: '/guide/' },
      { text: 'Reference', link: '/reference/TRACEABILITY_MAP' },
      { text: 'Governance', link: '/governance/ADR-001-external-package-adoption' },
      { text: 'Adoption', link: '/adoption/' },
    ],
  },
  {
    text: 'Languages',
    collapsed: true,
    items: [
      { text: 'فارسی', link: '/fa/' },
      { text: 'فارسی (لاتین)', link: '/fa-Latn/' },
      { text: '简体中文', link: '/zh-CN/' },
      { text: '繁體中文', link: '/zh-TW/' },
    ],
  },
]

const specsSidebar: DefaultTheme.SidebarItem[] = [
  {
    text: 'Feature Specs',
    items: [
      { text: '001: Spec-Driven Development Engine', link: '/specs/001-spec-driven-development-engine/' },
      { text: '002: Org-Wide Release Governance', link: '/specs/002-org-wide-release-governance-dx-automation/' },
      { text: '004: Modules and Cycles', link: '/specs/004-modules-and-cycles/' },
      { text: '005: heliosapp Completion', link: '/specs/005-heliosapp-completion/' },
      { text: '006: helioscli Completion', link: '/specs/006-helioscli-completion/' },
      { text: '007: thegent Completion', link: '/specs/007-thegent-completion/' },
    ],
  },
]

const config = withMermaid({
  title: 'HexaKit',
  description: 'Phenotype repos shelf: ~30 independent projects for AI-augmented software engineering.',
  appearance: 'dark',
  lastUpdated: true,
  ignoreDeadLinks: true,
  srcExclude: ['worklogs/**', 'research/**', 'reports/**', 'sessions/**', 'audits/**'],
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Guide', link: '/guide/' },
      { text: 'Specs', link: '/specs/' },
      { text: 'Reference', link: '/reference/TRACEABILITY_MAP' },
      { text: 'Governance', link: '/governance/ADR-001-external-package-adoption' },
      { text: 'Adoption', link: '/adoption/' },
    ],
    sidebar: {
      '/reference/': referenceSidebar,
      '/guide/': [
        {
          text: 'Guide',
          items: [{ text: 'Getting started', link: '/guide/' }],
        },
      ],
      '/governance/': [
        {
          text: 'Governance',
          items: [
            {
              text: 'ADR-001 external package adoption',
              link: '/governance/ADR-001-external-package-adoption',
            },
          ],
        },
      ],
      '/adoption/': adoptionSidebar,
      '/specs/': specsSidebar,
      '/fa/': overviewSidebar,
      '/fa-Latn/': overviewSidebar,
      '/zh-CN/': overviewSidebar,
      '/zh-TW/': overviewSidebar,
      '/': overviewSidebar,
    },
    search: { provider: 'local' },
  },
  mermaid: { theme: 'dark' },
})

const mermaidMarkdownConfig = config.markdown?.config

config.markdown = {
  ...config.markdown,
  config(md) {
    mermaidMarkdownConfig?.(md)
    md.core.ruler.after('inline', 'escape_placeholder_angle_tokens', (state) => {
      for (const token of state.tokens) {
        const children = token.children ?? []

        for (const child of children) {
          if (child.type === 'html_inline') {
            child.content = escapePlaceholderAngles(child.content)

            if (child.content.includes('&lt;')) {
              child.type = 'text'
              child.tag = ''
              child.nesting = 0
            }
          } else if (child.type === 'text' || child.type === 'code_inline') {
            child.content = escapePlaceholderAngles(child.content)
          }
        }
      }
    })
  },
}

export default config
