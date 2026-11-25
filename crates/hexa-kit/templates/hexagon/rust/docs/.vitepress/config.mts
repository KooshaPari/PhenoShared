import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Hexacore',
  description: 'Workspace template and tooling for Phenotype kits',
  base: '/hexacore/',
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Kits', link: '/kits' },
    ],
    sidebar: [
      {
        text: 'Guide',
        items: [
          { text: 'Overview', link: '/' },
          { text: 'Kits', link: '/kits' },
        ]
      }
    ]
  }
})
