# Functional Requirements -- phenodocs

**Version:** 1.1
**Date:** 2026-03-26

---

## FR-HUB: Hub Site

### FR-HUB-001: Local Dev Server
The `bun run dev` command SHALL start a VitePress dev server at `http://localhost:5173` serving the aggregated documentation site.
**Traces to:** E1.1
**Code:** `docs/.vitepress/config.ts`, `package.json#scripts.dev`

### FR-HUB-002: Top-Level Navigation
The site SHALL expose a top-level nav bar with items: Home (`/`), Wiki (`/wiki/`), Development Guide (`/development/`), Document Index (`/index/`), API (`/api/`), Roadmap (`/roadmap/`).
**Traces to:** E1.1
**Code:** `docs/.vitepress/config.ts#themeConfig.nav`

### FR-HUB-003: Per-Section Sidebar
The site SHALL render a section-specific sidebar for each top-level route (`/wiki/`, `/development/`, `/index/`, `/api/`, `/roadmap/`).
**Traces to:** E1.1
**Code:** `docs/.vitepress/config.ts#themeConfig.sidebar`

### FR-HUB-004: Full-Text Local Search
The site SHALL provide full-text search across all content using VitePress's `provider: 'local'` search integration.
**Traces to:** E1.1
**Code:** `docs/.vitepress/config.ts#themeConfig.search`

### FR-HUB-005: Document Index Sub-Routes
The `/index/` section SHALL provide sub-routes: `raw-all`, `planning`, `specs`, `research`, `worklogs`, `other`.
**Traces to:** E1.3
**Code:** `docs/.vitepress/config.ts#sidebar./index/`, `docs/index/`

### FR-HUB-006: Content Layer Types
The system SHALL define `DocLayer` as `{ level: 0 | 1 | 2 | 3 | 4; label: string }` representing: 0=ephemeral, 1=lab, 2=docs, 3=audit, 4=kb.
**Traces to:** E1.2
**Code:** `packages/docs/src/types/index.ts#DocLayer`

### FR-HUB-007: Static Build Output
`bun run build` SHALL produce a complete static site (HTML, CSS, JS, assets) in `docs/.vitepress/dist/` with clean URLs enabled.
**Traces to:** E3.1, E3.4
**Code:** `docs/.vitepress/config.ts#cleanUrls`, `package.json#scripts.build`

---

## FR-CFG: Config Factory (`createPhenotypeConfig`)

### FR-CFG-001: Factory Function Export
`createPhenotypeConfig` SHALL be exported from `@phenotype/docs/config` (`packages/docs/src/config/index.ts`).
**Traces to:** E2.1
**Code:** `packages/docs/src/config/index.ts`

### FR-CFG-002: ConfigOptions Interface
The factory SHALL accept a `ConfigOptions` object with fields: `title: string`, `description: string`, `base?: string`, `srcDir?: string`, `githubOrg?: string`, `githubRepo?: string`, `nav?: DefaultTheme.NavItem[]`, `sidebar?: DefaultTheme.Sidebar`, `overrides?: Partial<UserConfig<DefaultTheme.Config>>`.
**Traces to:** E2.1
**Code:** `packages/docs/src/types/index.ts#ConfigOptions`

### FR-CFG-003: Defaults Applied
When not specified, the factory SHALL apply: `base='/'`, `srcDir='docs'`, `githubOrg='KooshaPari'`, `lang='en-US'`, `lastUpdated: true`, `cleanUrls: true`, `markdown.lineNumbers: true`, markdown theme `github-light`/`github-dark`, local search, outline `[2,3]`, `externalLinkIcon: true`.
**Traces to:** E2.1
**Code:** `packages/docs/src/config/index.ts#baseConfig`

### FR-CFG-004: Repo Slug Inference
When `githubRepo` is omitted, the factory SHALL infer it as `title.toLowerCase().replace(/\s+/g, '-')`.
**Traces to:** E2.1
**Code:** `packages/docs/src/config/index.ts` (line: `const repoSlug = githubRepo ?? ...`)

### FR-CFG-005: Edit Link Pattern
The factory SHALL set `editLink.pattern` to `https://github.com/${githubOrg}/${repoSlug}/edit/main/${srcDir}/:path`.
**Traces to:** E2.1
**Code:** `packages/docs/src/config/index.ts#themeConfig.editLink`

### FR-CFG-006: Consumer Overrides via deepMerge
The factory SHALL deep-merge the consumer's `overrides` object on top of the base config using `deepMerge`, such that arrays are concatenated and nested objects are recursed.
**Traces to:** E2.1, E2.3
**Code:** `packages/docs/src/config/index.ts` (last line), `packages/docs/src/utils/config-merger.ts`

---

## FR-SBR: Sidebar Auto-Generator (`generateSidebar`)

### FR-SBR-001: Function Export
`generateSidebar` SHALL be exported from `@phenotype/docs/utils` (`packages/docs/src/utils/sidebar-generator.ts`).
**Traces to:** E2.2
**Code:** `packages/docs/src/utils/sidebar-generator.ts`

### FR-SBR-002: Input Interface
`generateSidebar` SHALL accept `{ srcDir: string; prefix: string; capitalizeGroups?: boolean }`.
**Traces to:** E2.2
**Code:** `packages/docs/src/utils/sidebar-generator.ts#SidebarGenOptions`

### FR-SBR-003: index.md Placement
`index.md` found at any directory level SHALL be emitted as `{ text: 'Overview', link: '<prefix>/' }` and placed first in the items array before other entries.
**Traces to:** E2.2
**Code:** `packages/docs/src/utils/sidebar-generator.ts#buildItems`

### FR-SBR-004: Subdirectory Groups
Subdirectories SHALL become collapsible `SidebarItem` groups (`collapsed: true`) with their children recursed via `buildItems`.
**Traces to:** E2.2
**Code:** `packages/docs/src/utils/sidebar-generator.ts#buildItems` (isDirectory branch)

### FR-SBR-005: Markdown File Items
Files ending in `.md` (excluding `index.md`) SHALL become link items with their base name title-cased and hyphens replaced by spaces.
**Traces to:** E2.2
**Code:** `packages/docs/src/utils/sidebar-generator.ts#buildItems` (`.md` branch)

### FR-SBR-006: Missing Directory Graceful Return
When the resolved directory does not exist, `generateSidebar` SHALL return `[]` without throwing.
**Traces to:** E2.2
**Code:** `packages/docs/src/utils/sidebar-generator.ts#buildItems` (try/catch on `readdirSync`)

---

## FR-MRG: Deep-Merge Utility (`deepMerge`)

### FR-MRG-001: Function Export
`deepMerge` SHALL be exported from `@phenotype/docs/utils` (`packages/docs/src/utils/config-merger.ts`).
**Traces to:** E2.3
**Code:** `packages/docs/src/utils/config-merger.ts`

### FR-MRG-002: Primitive Override
For a given key, if both `target` and `source` hold primitive values, the `source` value SHALL win.
**Traces to:** E2.3

### FR-MRG-003: Array Concatenation
When both `target[key]` and `source[key]` are arrays, the result SHALL be `[...target[key], ...source[key]]`.
**Traces to:** E2.3

### FR-MRG-004: Object Recursion
When both `target[key]` and `source[key]` are non-null, non-array objects, `deepMerge` SHALL recurse into them.
**Traces to:** E2.3

### FR-MRG-005: Immutability
Neither `target` nor `source` SHALL be mutated; the function SHALL return a new object via spread.
**Traces to:** E2.3

---

## FR-CMP: Vue Component Library

### FR-CMP-001: Global Registration
The theme entry (`packages/docs/src/theme/index.ts`) SHALL register all 21 Vue components globally via `app.component(name, component)` in the `enhanceApp` hook.
**Traces to:** E2.4
**Code:** `packages/docs/src/theme/index.ts#enhanceApp`

### FR-CMP-002: Component Inventory
The following 21 components SHALL be registered: `AuditTimeline`, `BackToTop`, `Breadcrumb`, `Callout`, `CategorySwitcher`, `CodeAnnotation`, `CodePlayground`, `ContentTabs`, `DemoGif`, `DocStatusBadge`, `KBGraph`, `LoadingSpinner`, `ModuleSwitcher`, `NavTabs`, `OpenAPI`, `StickyHeader`, `StickySidebar`, `Toast`, `ToastContainer`, `Tooltip`, `CommitLog`.
**Traces to:** E2.4
**Code:** `packages/docs/src/theme/components/`

### FR-CMP-003: Named Exports
All components SHALL also be exported as named exports from the theme entry for selective import by consumers.
**Traces to:** E2.4
**Code:** `packages/docs/src/theme/index.ts` (named export section)

### FR-CMP-004: CSS Import
The theme entry SHALL import `../css/custom.css`, which in turn imports `@phenotype/design/css/vitepress-theme.css`, so Phenotype keycap-palette and site-wide styles are applied to all consumers.
**Traces to:** E2.4
**Code:** `packages/docs/src/theme/index.ts` (`import '../css/custom.css'`)

---

## FR-PKG: Package Publishing

### FR-PKG-001: GitHub Packages Registry
`packages/docs/package.json` SHALL set `publishConfig.registry` to `https://npm.pkg.github.com` and `publishConfig.access` to `"public"`.
**Traces to:** E2.5
**Code:** `packages/docs/package.json#publishConfig`

### FR-PKG-002: Export Map Completeness
`packages/docs/package.json` SHALL define exports for: `./theme`, `./config`, `./utils`, `./types`, `./css/custom.css`. Keycap tokens SHALL be consumed from `@phenotype/design/css/keycap-palette.css`.
**Traces to:** E2.5
**Code:** `packages/docs/package.json#exports`

### FR-PKG-003: Workspace Dependency
The hub `package.json` SHALL declare `"@phenotype/docs": "workspace:*"` as a dependency.
**Traces to:** E2.5
**Code:** `package.json#dependencies`

---

## FR-QAL: Quality and CI

### FR-QAL-001: TypeScript Strict Check
`bun run typecheck` (vue-tsc --noEmit) SHALL exit 0 on a clean tree with no implicit `any` in exported types.
**Traces to:** E3.1
**Code:** `package.json#scripts.typecheck`, `tsconfig.json`

### FR-QAL-002: Oxlint Zero Errors
`bun run lint:ts` (oxlint against `.vitepress/`) SHALL exit 0 on a clean tree.
**Traces to:** E3.2
**Code:** `package.json#scripts.lint:ts`, `oxlint.json`

### FR-QAL-003: Markdownlint Zero Errors
`bun run lint` (markdownlint-cli against `docs/**/*.md`) SHALL exit 0 on a clean tree.
**Traces to:** E3.2
**Code:** `package.json#scripts.lint`

### FR-QAL-004: Link Check Script
`scripts/check_docs_links.py` SHALL be runnable via `uv run python scripts/check_docs_links.py`, exit 0 for a valid tree, and exit non-zero with actionable output for broken links.
**Traces to:** E3.3
**Code:** `scripts/check_docs_links.py`

### FR-QAL-005: GitHub Pages Deployment
The CI `deploy.yml` workflow SHALL deploy the static build (`docs/.vitepress/dist/`) to GitHub Pages on merge to `main`.
**Traces to:** E3.4
