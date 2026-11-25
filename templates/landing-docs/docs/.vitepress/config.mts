import { defineConfig } from 'vitepress'

// Set title, description and base per repo. base is '/<repo>/' on github.io.
export default defineConfig({
  title: 'Project name',
  description: 'One line description',
  base: '/',
  cleanUrls: true,
  themeConfig: {
    nav: [
      { text: 'Docs', link: '/guide/' },
      { text: 'Compete', link: '/compete/' }
    ],
    sidebar: [
      { text: 'Guide', link: '/guide/' },
      { text: 'Compete', link: '/compete/' }
    ]
  }
})
