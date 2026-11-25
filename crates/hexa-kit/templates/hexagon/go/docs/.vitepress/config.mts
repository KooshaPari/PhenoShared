import { defineConfig } from 'vitepress';
import { createSiteMeta } from './site-meta.mjs';

const siteMeta = createSiteMeta();

export default defineConfig({
  title: 'go-hex',
  description: 'Hexagonal architecture kit for Go',
  lang: 'en-US',
  srcDir: '.',
  outDir: '../.vitepress-dist',
  head: [['meta', { name: 'theme-color', content: '#0f766e' }]],
  themeConfig: {
    nav: [
      { text: 'Home', link: siteMeta.locales.root },
      { text: 'ADR', link: '/adr/ADR-001-hexagonal-architecture' },
    ],
    sidebar: [
      { text: 'Start', items: [{ text: 'Docs', link: '/' }] },
      {
        text: 'Reference',
        items: [{ text: 'ADR-001', link: '/adr/ADR-001-hexagonal-architecture' }],
      },
    ],
    socialLinks: [],
  },
});
