import { defineConfig } from 'vitepress'

// Minimal VitePress configuration for the Logify / logkit documentation site.
// Deployed automatically to GitHub Pages by .github/workflows/docs.yml.
export default defineConfig({
  title: 'Logify',
  description: 'Zero-cost structured logging framework for Rust (logkit crate).',
  base: '/Logify/',
  lastUpdated: true,
  cleanUrls: true,
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Getting Started', link: '/getting-started' }
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
      { icon: 'github', link: 'https://github.com/KooshaPari/Logify' }
    ],
    footer: {
      message: 'Released under the MIT OR Apache-2.0 license.',
      copyright: 'Copyright (c) Logify contributors.'
    }
  }
})
