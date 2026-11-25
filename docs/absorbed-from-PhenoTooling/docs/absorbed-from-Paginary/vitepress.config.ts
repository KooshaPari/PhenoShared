import { defineConfig } from 'vitepress'

export default defineConfig({
  ignoreDeadLinks: true,

  title: 'Paginary',
  description: 'Phenotype knowledge collection — handbooks, specs, X-driven dev, and user journeys',
  lang: 'en-US',
  appearance: 'dark',
  lastUpdated: true,

  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
    ['link', { href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap', rel: 'stylesheet' }],
  ],

  markdown: {
    image: {
      lazyLoading: true,
    },
    container: {
      tipLabel: 'TIP',
      warningLabel: 'WARNING',
      dangerLabel: 'DANGER',
      infoLabel: 'INFO',
      detailsLabel: 'Details',
    },
  },

  themeConfig: {
    logo: '/logo.svg',
    siteTitle: 'Paginary',

    nav: [
      { text: 'Handbook', link: '/handbook/' },
      { text: 'Specs', link: '/specs/' },
      { text: 'X-Driven Dev', link: '/xdd/' },
      { text: 'Journeys', link: '/journeys/' },
    ],

    sidebar: {
      '/handbook/': [
        {
          text: 'PhenoHandbook',
          items: [
            { text: 'Introduction', link: '/handbook/' },
          ],
        },
      ],
      '/specs/': [
        {
          text: 'PhenoSpecs',
          items: [
            { text: 'Overview', link: '/specs/' },
          ],
        },
      ],
      '/xdd/': [
        {
          text: 'X-Driven Development',
          items: [
            { text: 'Overview', link: '/xdd/' },
          ],
        },
      ],
      '/journeys/': [
        {
          text: 'User Journeys',
          items: [
            { text: 'Overview', link: '/journeys/' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/KooshaPari/phenotype-infrakit' },
    ],

    footer: {
      message: 'Phenotype knowledge collection.',
      copyright: 'Copyright © 2025-present Phenotype Contributors',
    },

    search: {
      provider: 'local',
    },
  },
})
