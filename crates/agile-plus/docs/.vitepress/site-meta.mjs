import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { readdirSync, statSync } from 'node:fs'
import { generateSidebar } from '@phenotype/docs/utils'

const __dirname = dirname(fileURLToPath(import.meta.url))
// docs/.vitepress -> docs (the VitePress srcDir)
const docsSrcDir = join(__dirname, '..')

// Top-level docs sections that contain real, navigable content.
// Each becomes both a nav entry and an auto-generated sidebar group,
// scoped so it only shows while browsing under that section's path.
const SECTIONS = [
  { prefix: 'architecture', text: 'Architecture' },
  { prefix: 'guide', text: 'Guide' },
  { prefix: 'sdk', text: 'SDK' },
  { prefix: 'reference', text: 'Reference' },
  { prefix: 'process', text: 'Process' },
  { prefix: 'workflow', text: 'Workflow' },
]

// None of these sections ship an index.md, so a nav link to `/${prefix}/`
// would 404 (VitePress has no page to serve at the bare directory route).
// Find the first real markdown file in each section (same alphabetical/
// index-first order generateSidebar uses) and link there instead.
function findFirstDoc(dir, linkPrefix) {
  let entries
  try {
    entries = readdirSync(dir).sort()
  } catch {
    return null
  }
  if (entries.includes('index.md')) return `${linkPrefix}/`
  for (const entry of entries) {
    const full = join(dir, entry)
    const stat = statSync(full)
    if (stat.isDirectory()) {
      const found = findFirstDoc(full, `${linkPrefix}/${entry}`)
      if (found) return found
    } else if (entry.endsWith('.md')) {
      const name = entry.slice(0, -3)
      return `${linkPrefix}/${name}`
    }
  }
  return null
}

function buildSidebar() {
  const sidebar = {}
  for (const { prefix } of SECTIONS) {
    sidebar[`/${prefix}/`] = generateSidebar({ srcDir: docsSrcDir, prefix })
  }
  return sidebar
}

function buildSectionNav() {
  return SECTIONS.map(({ prefix, text }) => ({
    text,
    link: findFirstDoc(join(docsSrcDir, prefix), `/${prefix}`) || `/${prefix}/`,
  }))
}

export function createSiteMeta({ base = '/' } = {}) {
  // For custom domain deployments (e.g., agileplus.phenotype.space), use root base
  // GitHub Pages default URLs include repo name prefix, but custom domains serve from root
  const isCustomDomain = process.env.PHENOTYPE_CUSTOM_DOMAIN === 'true'
  const resolvedBase = isCustomDomain ? '/' : base

  return {
    base: resolvedBase,
    // VitePress resolves `srcDir` relative to the process cwd, which is
    // `docs/` (the working-directory for `bun run docs:build`). The actual
    // markdown content lives directly in this directory, not a nested
    // `docs/docs/`, so srcDir must be '.', not the '@phenotype/docs' default
    // of 'docs'. Without this override VitePress only ever discovers
    // `docs/index.md` (the Home hero) and treats all real content as
    // unreachable, which is the root cause of the missing-sidebar bug.
    srcDir: '.',
    title: 'AgilePlus',
    description: 'AgilePlus — a lightweight, standalone project-management and PM substrate: requirements, epics, stories, and repo sync, from the CLI or as an embedded library.',
    sidebar: buildSidebar(),
    // Only the sections wired into nav/sidebar above are curated, navigable
    // docs. The rest of this directory holds specs, archives, worklogs, etc.
    // that are not part of the public doc site and in some cases (e.g.
    // specs/**) contain frontmatter VitePress can't parse as YAML. Excluding
    // them keeps the build fast and avoids pulling unrelated/broken content
    // into the site. `overrides` is deep-merged over the base VitePress
    // config by createPhenotypeConfig, so this is the correct place for a
    // raw VitePress option like srcExclude that isn't one of its named
    // top-level ConfigOptions fields.
    overrides: {
      srcExclude: [
        '_archive/**', 'adr/**', 'agents/**', 'assets/**', 'audit/**',
        'audits/**', 'boundary/**', 'changes/**', 'checklists/**',
        'concepts/**', 'developers/**', 'docs/**', 'doc-system/**',
        'embeds/**', 'examples/**', 'fa/**', 'fa-Latn/**',
        'frontend-candidates/**', 'guides/**', 'harmonization/**',
        'infra/**', 'intent/**', 'issues/**', 'journeys/**', 'operations/**',
        'pilot/**', 'plans/**', 'remediation/**', 'reports/**',
        'requirements/**', 'research/**', 'roadmap/**', 'security/**',
        'sessions/**', 'sota/**', 'specs/**', 'superpowers/**',
        'templates/**', 'tests/**', 'triage/**', 'vendor/**',
        'worklogs/**', 'zh-CN/**', 'zh-TW/**',
      ],
    },
    themeConfig: {
      siteTitle: 'AgilePlus',
      nav: [
        { text: 'Home', link: resolvedBase || '/' },
        ...buildSectionNav(),
      ],
      socialLinks: [
        { icon: 'github', link: 'https://github.com/<REDACTED>/AgilePlus' },
      ],
    },
    head: [
      ['meta', { name: 'theme-color', content: '#7ebab5' }],
    ],
  }
}
