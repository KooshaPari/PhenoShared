import { withMermaid } from 'vitepress-plugin-mermaid'

export default withMermaid({
  title: 'phenotype-auth-ts',
  description: 'TypeScript OAuth2 / OIDC authentication patterns with hexagonal architecture',
  appearance: 'dark',
  lastUpdated: true,
  themeConfig: {
    nav: [{ text: 'Home', link: '/' }],
    sidebar: [
      {
        text: 'Guide',
        items: [
          { text: 'Getting Started', link: '/getting-started' },
        ],
      },
    ],
    search: { provider: 'local' },
  },
  mermaid: { theme: 'dark' },
})
