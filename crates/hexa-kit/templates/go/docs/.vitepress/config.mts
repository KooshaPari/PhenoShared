import { defineConfig } from 'vitepress';
import { createSiteMeta } from './site-meta.mjs';

const siteMeta = createSiteMeta();

export default defineConfig({
  title: 'template-lang-go',
  description: 'Language template layer for Go',
  lang: 'en-US',
  srcDir: '.',
  outDir: '../.vitepress-dist',
  head: [['meta', { name: 'theme-color', content: '#1f2937' }]],
  themeConfig: {
    nav: [
      { text: 'Home', link: siteMeta.locales.root },
      { text: 'Branch Protection', link: '/BRANCH_PROTECTION' },
      { text: 'Upgrade', link: '/UPGRADE' },
    ],
    sidebar: [
      { text: 'Start', items: [{ text: 'Docs', link: '/' }] },
      {
        text: 'Reference',
        items: [
          { text: 'Branch Protection', link: '/BRANCH_PROTECTION' },
          { text: 'Upgrade', link: '/UPGRADE' },
        ],
      },
    ],
    socialLinks: [],
  },
});
