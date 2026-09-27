import type { DefaultTheme, UserConfig } from 'vitepress'

export interface ProjectMeta {
  /** Display name of the project */
  name: string
  /** URL-safe slug used in routing */
  slug: string
  /** Short description */
  description?: string
  /** GitHub repository path (org/repo) */
  repo?: string
  /** Documentation source directory relative to project root */
  srcDir?: string
}

export interface DocLayer {
  /** Layer number (0-4) for badge styling */
  level: 0 | 1 | 2 | 3 | 4
  /** Layer label */
  label: string
}

export interface ConfigOptions {
  /** Site title */
  title: string
  /** Site description */
  description: string
  /** Base path for deployment (default: '/') */
  base?: string
  /** Source directory for docs (default: 'docs') */
  srcDir?: string
  /** GitHub org or user */
  githubOrg?: string
  /** GitHub repo name */
  githubRepo?: string
  /** Navigation items (merged with defaults) */
  nav?: DefaultTheme.NavItem[]
  /** Sidebar config (merged with defaults) */
  sidebar?: DefaultTheme.Sidebar
  /** VitePress i18n locale definitions */
  locales?: UserConfig<DefaultTheme.Config>['locales']
  /** Additional VitePress config to deep-merge */
  overrides?: Partial<UserConfig<DefaultTheme.Config>>
}
