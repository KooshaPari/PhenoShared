// Edited 2026-05-04 (frontend-engineer task):
//   Fixed broken phenodocsTheme / phenodocsRoot references. These variables
//   were never defined, causing a ReferenceError if this config was ever
//   loaded directly (e.g. `vitepress dev docs/`). The root config at
//   .vitepress/config.mts is the canonical entry point; this inner config
//   is kept for reference but the broken alias/fs-allow entries are removed.
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { defineConfig } from 'vitepress'

const __dirname = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  title: 'PhenoDocs',
  description: 'PhenoDocs documentation',
  srcDir: '.',
  lastUpdated: true,
  cleanUrls: true,
  ignoreDeadLinks: true,

  vite: {
    resolve: {
      alias: {
        '@phenodocs-theme': resolve(__dirname, '../../.vitepress/theme'),
      },
    },
    server: {
      fs: {
        // Allow serving files from the phenodocs workspace root so that
        // VitePress can resolve theme assets during local dev.
        allow: [resolve(__dirname, '../../..')],
      },
    },
  },
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Governance', link: '/governance/overview' },
      { text: 'Wiki', link: '/wiki/' },
      { text: 'Development Guide', link: '/development/' },
      { text: 'Document Index', link: '/index/' },
      { text: 'API', link: '/api/' },
      { text: 'Roadmap', link: '/roadmap/' }
    ],
    sidebar: {
      '/governance/': [
        { text: 'Governance', items: [
          { text: 'Overview', link: '/governance/overview' },
          { text: 'Journey Traceability', link: '/governance/journeys' }
        ]}
      ],
      '/wiki/': [
        { text: 'Wiki (User Guides)', items: [
          { text: 'Overview', link: '/wiki/' }
        ]}
      ],
      '/development/': [
        { text: 'Development Guide', items: [
          { text: 'Overview', link: '/development/' }
        ]}
      ],
      '/index/': [
        { text: 'Document Index', items: [
          { text: 'Overview', link: '/index/' },
          { text: 'Raw/All', link: '/index/raw-all' },
          { text: 'Planning', link: '/index/planning' },
          { text: 'Specs', link: '/index/specs' },
          { text: 'Research', link: '/index/research' },
          { text: 'Worklogs', link: '/index/worklogs' },
          { text: 'Other', link: '/index/other' }
        ]}
      ],
      '/api/': [
        { text: 'API', items: [
          { text: 'Overview', link: '/api/' }
        ]}
      ],
      '/roadmap/': [
        { text: 'Roadmap', items: [
          { text: 'Overview', link: '/roadmap/' }
        ]}
      ],
      '/': [
        { text: 'Quick Links', items: [
          { text: 'Governance', link: '/governance/overview' },
          { text: 'Wiki', link: '/wiki/' },
          { text: 'Development Guide', link: '/development/' },
          { text: 'Document Index', link: '/index/' },
          { text: 'API', link: '/api/' },
          { text: 'Roadmap', link: '/roadmap/' }
        ]}
      ]
    },
    search: { provider: 'local' },
    socialLinks: [{ icon: 'github', link: 'https://github.com/kooshapari/phenodocs' }]
  }
})
