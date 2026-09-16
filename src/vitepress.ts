// Copyright (c) 2026 Phenotype Enterprise. All rights reserved.
// Licensed under the Phenotype Standard License.

/**
 * VitePress theme helper for Phenotype projects.
 *
 * Usage in your .vitepress/theme/index.ts:
 *
 *   import DefaultTheme from 'vitepress/theme'
 *   import '@phenotype/design/css/keycap-palette.css'
 *   // or: import '@phenotype/design/css/vitepress-theme.css'
 *   export default { extends: DefaultTheme }
 */

export const vitepressMarkdownTheme = {
  light: 'github-light',
  dark: 'vitesse-dark',
} as const

export const vitepressConfig = {
  appearance: 'dark' as const,
  markdown: {
    lineNumbers: true,
    theme: vitepressMarkdownTheme,
  },
}
