// Edited 2026-05-04 (frontend-engineer task):
//   Fix shared VitePress asset handling so favicon/logo do not 404 on
//   GitHub Pages deployments where `base` is `/<repo>/`.
//   Changes:
//     1. Normalize `base` to always end with `/` before composing asset URLs.
//        VitePress requires the trailing slash; without it `${base}favicon.svg`
//        becomes `/repofavicon.svg` and 404s.
//     2. Switch favicon from `.ico` (which did not exist in any consumer's
//        public/ tree) to `favicon.svg` — checked-in placeholders ship with
//        phenodocs/docs/public/ because this site uses `srcDir: 'docs'`.
//        Add an `apple-touch-icon` referencing the same.
//     3. Drop the `.ico` reference entirely; SVG favicons are supported by all
//        evergreen browsers VitePress targets.
//     4. `themeConfig.logo` is left as a root-relative path ('/logo.svg');
//        VitePress auto-prefixes `themeConfig.logo` with `base`, so consumers
//        must NOT prepend `${base}` themselves (would double-prefix).
//     5. `head` entries are NOT auto-prefixed by VitePress, so we DO prepend
//        the normalized `base` for those.
import { defineConfig } from 'vitepress'
import type { ConfigOptions } from '../types/index.ts'
import { deepMerge } from '../utils/config-merger.ts'

/**
 * Create a VitePress config pre-loaded with the Phenotype keycap theme defaults.
 *
 * Consumers call this in their `.vitepress/config.mts`:
 * ```ts
 * import { createPhenotypeConfig } from '@phenotype/docs/config'
 * export default createPhenotypeConfig({ title: 'My Project', description: '...' })
 * ```
 */
export function createPhenotypeConfig(options: ConfigOptions) {
  const {
    title,
    description,
    base = '/',
    srcDir = 'docs',
    githubOrg = 'KooshaPari',
    githubRepo,
    nav = [],
    sidebar = {},
    locales,
    overrides = {},
  } = options

  const repoSlug = githubRepo ?? title.toLowerCase().replace(/\s+/g, '-')

  // Normalize base: VitePress requires leading + trailing slash. Without trailing
  // slash, `${base}favicon.svg` produces a malformed URL (e.g. `/repofavicon.svg`).
  const normalizedBase = base.endsWith('/') ? base : `${base}/`

  const baseConfig = defineConfig({
    title,
    description,
    lang: 'en-US',
    srcDir,
    base: normalizedBase,
    ...(locales !== undefined ? { locales } : {}),
    lastUpdated: true,
    cleanUrls: true,

    head: [
      // SVG favicon. Phenodocs ships placeholder at `docs/public/favicon.svg`
      // (VitePress resolves `public/` relative to `srcDir`, not repo root).
      // Each consumer must ship its own under `<srcDir>/public/` to override.
      ['link', { rel: 'icon', type: 'image/svg+xml', href: `${normalizedBase}favicon.svg` }],
      ['link', { rel: 'apple-touch-icon', href: `${normalizedBase}favicon.svg` }],
    ],

    themeConfig: {
      siteTitle: title,

      nav,

      sidebar,

      socialLinks: [
        { icon: 'github', link: `https://github.com/${githubOrg}/${repoSlug}` },
      ],

      footer: {
        message: 'Released under the MIT License.',
        copyright: `Copyright \u00a9 ${new Date().getFullYear()} Phenotype`,
      },

      search: {
        provider: 'local',
      },

      editLink: {
        pattern: `https://github.com/${githubOrg}/${repoSlug}/edit/main/${srcDir}/:path`,
        text: 'Edit this page on GitHub',
      },

      outline: {
        level: [2, 3],
        label: 'On this page',
      },

      externalLinkIcon: true,
    },

    markdown: {
      lineNumbers: true,
      theme: {
        light: 'github-light',
        dark: 'github-dark',
      },
    },

    ignoreDeadLinks: true,
  })

  // Deep-merge consumer overrides on top of base config
  return deepMerge(baseConfig, overrides) as ReturnType<typeof defineConfig>
}
