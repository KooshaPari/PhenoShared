import { localeConfig, nav, sidebar } from '../../.vitepress/site-meta.mjs'

export function getSiteMeta() {
  return {
    title: 'phenotype-xdd-lib',
    nav,
    sidebar,
    locales: Object.keys(localeConfig).filter((key) => key !== 'root')
  }
}
