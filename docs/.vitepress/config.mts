import { defineConfig } from 'vitepress'

// Pine documentation site (VitePress).
// Content lives under `docs/src/` so we don't clobber the auto-generated
// `docs/index.md` (the mdbook-style cross-reference index) at the top of
// `docs/`. VitePress builds the Markdown site from this `srcDir`.
export default defineConfig({
  srcDir: 'src',
  cleanUrls: true,
  title: 'Pine',
  titleTemplate: ':title — Pine',
  description:
    'Pine is a Wine-equivalent runtime compatibility layer that translates Windows, macOS, and Linux applications into Phenotype-native execution environments.',
  lastUpdated: true,
  ignoreDeadLinks: true,
  head: [
    ['meta', { name: 'theme-color', content: '#0b3d2e' }],
    ['meta', { property: 'og:title', content: 'Pine' }],
    [
      'meta',
      {
        property: 'og:description',
        content:
          'Wine-equivalent compatibility layer for Phenotype — translate Windows, macOS, and Linux apps into Phenotype execution environments.'
      }
    ]
  ],
  themeConfig: {
    siteTitle: 'Pine',
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Getting Started', link: '/getting-started' },
      {
        text: 'Repository',
        link: 'https://github.com/KooshaPari/Pine'
      }
    ],
    sidebar: [
      {
        text: 'Introduction',
        items: [
          { text: 'Overview', link: '/' },
          { text: 'Getting Started', link: '/getting-started' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/KooshaPari/Pine' }
    ],
    footer: {
      message: 'Released under the MIT OR Apache-2.0 license.',
      copyright: 'Copyright (c) 2026 Phenotype contributors'
    }
  }
})
