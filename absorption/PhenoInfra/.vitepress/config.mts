// Edited 2026-05-04 (frontend-engineer task):
//   Fix shared VitePress asset 404s on GitHub Pages.
//   Changes:
//     1. `themeConfig.logo` left as '/logo.svg' — VitePress automatically
//        prefixes themeConfig.logo with `base`, so DO NOT prepend `${base}`
//        manually (would produce `/phenodocs/phenodocs/logo.svg`).
//     2. Favicon is now wired via `createPhenotypeConfig`'s shared `head[]`
//        which prepends the normalized `base` for non-auto-prefixed entries.
//        Static assets (favicon.svg, logo.svg) live in `docs/public/` because
//        VitePress resolves `public/` relative to `srcDir: 'docs'`.
//     3. `docsBase` is normalized to always end with `/` — required by
//        VitePress for correct asset URL composition under GitHub Pages.
//
// Edited 2026-06-16 (a11y-baseline AT4/AT5):
//   Add `locales` block to enable VitePress built-in i18n with two locales
//   (English, Spanish) plus Arabic RTL coverage. Per-locale `dir` is set
//   on the root layout by VitePress, satisfying the AT5 rtl requirement.
import { createPhenotypeConfig } from '../packages/docs/src/config/index.ts'

// Environment-based configuration for GitHub Pages compatibility.
// On Pages, repo lives at `/<repo>/`; locally and on a custom domain root, `/`.
const isPagesBuild = process.env.GITHUB_ACTIONS === 'true' || process.env.GITHUB_PAGES === 'true'
const repoName = process.env.GITHUB_REPOSITORY?.split('/')[1] || 'phenodocs'
const rawBase = isPagesBuild ? `/${repoName}/` : '/'
// Defensive: ensure leading + trailing slash even if repoName was malformed.
const docsBase = (rawBase.startsWith('/') ? rawBase : `/${rawBase}`).replace(/\/+$/, '/') || '/'

export default createPhenotypeConfig({
  title: 'PhenoDocs',
  description: 'Federation hub for multi-project documentation',
  lang: 'en-US',
  srcDir: 'docs',
  base: docsBase,
  githubOrg: 'KooshaPari',
  githubRepo: repoName,

  nav: [
    { text: 'Guide', link: '/guide/getting-started' },
    { text: 'Architecture', link: '/guide/architecture' },
    { text: 'API', link: '/reference/api' },
    { text: 'Governance', link: '/governance/overview' },
    { text: 'Roadmap', link: '/roadmap/' },
    { text: 'Workspace views', link: '/views/' },
  ],

  // VitePress built-in i18n (AT4 + AT5): English root, Spanish LTR, Arabic RTL.
  // VitePress automatically applies `<html dir="..." lang="...">` per-locale and
  // resolves content from `docs/<locale>/...` for non-root locales.
  locales: {
    root: {
      label: 'English',
      lang: 'en-US',
      dir: 'ltr',
      themeConfig: {
        nav: [
          { text: 'Guide', link: '/guide/getting-started' },
          { text: 'Architecture', link: '/guide/architecture' },
          { text: 'API', link: '/reference/api' },
          { text: 'Governance', link: '/governance/overview' },
          { text: 'Roadmap', link: '/roadmap/' },
          { text: 'Workspace views', link: '/views/' },
        ]
      }
    },
    es: {
      label: 'Español',
      lang: 'es-ES',
      dir: 'ltr',
      link: '/es/'
    },
    ar: {
      label: 'العربية',
      lang: 'ar',
      dir: 'rtl',
      link: '/ar/'
    }
  },

  themeConfig: {
    logo: '/logo.svg',
    siteTitle: 'PhenoDocs',

    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'Architecture', link: '/guide/architecture' },
      { text: 'API', link: '/reference/api' },
      { text: 'Governance', link: '/governance/overview' },
      { text: 'Roadmap', link: '/roadmap/' },
      { text: 'Workspace views', link: '/views/' }
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/guide/getting-started' },
            { text: 'Architecture', link: '/guide/architecture' },
            { text: 'Full-turn delivery', link: '/guides/full-turn-delivery' }
          ]
        }
      ],
      '/reference/': [
        {
          text: 'Reference',
          items: [
            { text: 'API', link: '/reference/api' }
          ]
        }
      ],
      '/governance/': [
        {
          text: 'Governance',
          items: [
            { text: 'Overview', link: '/governance/overview' },
            { text: 'Stacked PRs', link: '/governance/stacked-prs/' }
          ]
        }
      ],
      '/templates/': [
        {
          text: 'Templates',
          items: [
            { text: 'Release Matrix Template', link: '/templates/release-matrix-template' }
          ]
        }
      ],
      '/roadmap/': [
        {
          text: 'Roadmap',
          items: [
            { text: 'Overview', link: '/roadmap/' }
          ]
        }
      ],
      '/planning/': [
        {
          text: 'Planning',
          items: [
            { text: 'Rich workspace views', link: '/planning/rich-workspace-views' },
            { text: 'Full-turn Next 24', link: '/planning/full-turn-next24-20260326' }
          ]
        }
      ],
      '/views/': [
        {
          text: 'Workspace views',
          items: [
            { text: 'Overview', link: '/views/' },
            { text: 'Changelog (rich)', link: '/views/changelog' },
            { text: 'Commit log', link: '/views/commits' },
            { text: 'WBS & DAG', link: '/views/wbs' }
          ]
        }
      ]
    },

    socialLinks: [
      { icon: 'github', link: `https://github.com/kooshapari/${repoName}` }
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024 Kush Team'
    },

    search: {
      provider: 'local'
    },

    editLink: {
      pattern: `https://github.com/kooshapari/${repoName}/edit/main/docs/:path`,
      text: 'Edit this page on GitHub'
    },

    outline: {
      level: [2, 3],
      label: 'On this page'
    },

    externalLinkIcon: true,
    breadcrumb: true
  },

  overrides: {
    themeConfig: {
      logo: '/logo.svg',
      breadcrumb: true,
    },
    markdown: {
      anchorLinks: true,
    },
  },
})
