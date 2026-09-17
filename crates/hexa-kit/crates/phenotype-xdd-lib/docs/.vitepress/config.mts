import { defineConfig } from 'vitepress'
import { localeConfig, nav, sidebar } from './site-meta.mjs'

const repoName = process.env.GITHUB_REPOSITORY?.split('/')[1] || 'phenotype-xdd-lib'
const isPagesBuild = process.env.GITHUB_ACTIONS === 'true' || process.env.GITHUB_PAGES === 'true'
const base = isPagesBuild ? `/${repoName}/` : '/'

export default defineConfig({
  title: 'phenotype-xdd-lib',
  description: 'Cross-cutting xDD utilities for Rust projects',
  lang: 'en-US',
  base,
  cleanUrls: true,
  lastUpdated: true,
  locales: localeConfig,
  themeConfig: {
    siteTitle: 'phenotype-xdd-lib',
    nav,
    sidebar,
    footer: {
      message: 'Rust xDD utilities reference',
      copyright: 'Phenotype'
    },
    outline: {
      level: [2, 3]
    },
    docFooter: {
      prev: 'Previous page',
      next: 'Next page'
    },
    socialLinks: [{ icon: 'github', link: `https://github.com/<REDACTED>/${repoName}` }],
    search: { provider: 'local' }
  },
  markdown: {
    lineNumbers: true
  },
  ignoreDeadLinks: true
})
