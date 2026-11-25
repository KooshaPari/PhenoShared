import { readdirSync, statSync } from 'node:fs'
import { basename, join, relative } from 'node:path'
import type { DefaultTheme } from 'vitepress'

interface SidebarGenOptions {
  /** Absolute path to the docs source directory */
  srcDir: string
  /** Sub-path within srcDir to generate sidebar for (e.g. 'guide') */
  prefix: string
  /** Whether to capitalize directory names as group titles (default: true) */
  capitalizeGroups?: boolean
}

/**
 * Auto-generate a VitePress sidebar from directory structure.
 *
 * Each subdirectory becomes a collapsible group; markdown files become items.
 * Files are sorted alphabetically. `index.md` is placed first in each group.
 */
export function generateSidebar(
  options: SidebarGenOptions,
): DefaultTheme.SidebarItem[] {
  const { srcDir, prefix, capitalizeGroups = true } = options
  const dir = join(srcDir, prefix)

  return buildItems(dir, `/${prefix}`, capitalizeGroups)
}

function buildItems(
  dir: string,
  linkPrefix: string,
  capitalizeGroups: boolean,
): DefaultTheme.SidebarItem[] {
  let entries: string[]
  try {
    entries = readdirSync(dir).sort()
  } catch {
    return []
  }

  const items: DefaultTheme.SidebarItem[] = []

  // Process index.md first if it exists
  if (entries.includes('index.md')) {
    items.push({
      text: 'Overview',
      link: `${linkPrefix}/`,
    })
  }

  for (const entry of entries) {
    if (entry === 'index.md') continue
    const full = join(dir, entry)
    const stat = statSync(full)

    if (stat.isDirectory()) {
      const label = capitalizeGroups
        ? entry.charAt(0).toUpperCase() + entry.slice(1).replace(/-/g, ' ')
        : entry
      const children = buildItems(full, `${linkPrefix}/${entry}`, capitalizeGroups)
      if (children.length > 0) {
        items.push({ text: label, collapsed: true, items: children })
      }
    } else if (entry.endsWith('.md')) {
      const name = basename(entry, '.md')
      const label = name.charAt(0).toUpperCase() + name.slice(1).replace(/-/g, ' ')
      items.push({ text: label, link: `${linkPrefix}/${name}` })
    }
  }

  return items
}
