import { defineConfig } from 'vitepress';

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: 'Quillr',
  description: 'Multi-language HTTP toolkit for the Phenotype ecosystem.',
  cleanUrls: true,
  ignoreDeadLinks: true,
  // Exclude the pre-existing project markdown directories so VitePress does
  // not attempt to render them — they use a project-specific frontmatter
  // layout (e.g. `layout: doc`) that is not a valid VitePress layout.
  srcExclude: [
    'journeys/**',
    'research/**',
    'stories/**',
    'traceability/**',
    'node_modules/**',
    '.vitepress/cache/**',
    '.vitepress/dist/**',
  ],
  head: [
    ['meta', { name: 'theme-color', content: '#1f2937' }],
    ['meta', { property: 'og:title', content: 'Quillr' }],
    [
      'meta',
      {
        property: 'og:description',
        content: 'Multi-language HTTP toolkit for the Phenotype ecosystem.',
      },
    ],
  ],
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'Getting Started', link: '/getting-started' },
    ],
    sidebar: [
      {
        text: 'Introduction',
        items: [
          { text: 'What is Quillr?', link: '/' },
          { text: 'Getting Started', link: '/getting-started' },
        ],
      },
    ],
    socialLinks: [
      {
        icon: 'github',
        link: 'https://github.com/KooshaPari/Quillr',
      },
    ],
    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2026 Quillr contributors',
    },
    search: {
      provider: 'local',
    },
  },
});
