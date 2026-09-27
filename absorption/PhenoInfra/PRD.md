# Product Requirements Document -- phenodocs

**Version:** 1.1
**Date:** 2026-03-26
**Status:** Active

---

## Product Vision

PhenoDocs is a VitePress-based documentation federation hub for the Phenotype organization. It has two deliverables:

1. **Hub site** — a static VitePress site that aggregates docs from all Phenotype projects into a unified, searchable portal organized by layer (lab / docs / audit / kb) and category (planning, specs, research, worklogs).
2. **`@phenotype/docs` npm package** — a publishable workspace package (`packages/docs`) providing a shared VitePress theme, `createPhenotypeConfig` config factory, `generateSidebar` utility, `deepMerge` helper, typed interfaces, and a library of 21 Vue components — so any Phenotype project can adopt a consistent documentation experience without boilerplate.

---

## E1: Documentation Federation Hub

### E1.1: Unified Multi-Project Portal

As a developer, I can browse documentation from all Phenotype projects in one portal so I do not need to visit each repository individually.

**Acceptance Criteria:**
- `bun run dev` serves the hub locally at `http://localhost:5173`
- Top-level nav: Home, Wiki, Development Guide, Document Index, API, Roadmap
- Document Index sub-routes: `raw-all`, `planning`, `specs`, `research`, `worklogs`, `other`
- Full-text search (`provider: 'local'`) is available across all content
- `bun run build` produces a static site in `docs/.vitepress/dist/`

### E1.2: Layered Content Organization

As a reader, I can identify the maturity and audience of a document through its layer.

**Acceptance Criteria:**
- Five content layers are defined and typed in `@phenotype/docs/types`:
  - Level 0: ephemeral / raw (internal only)
  - Level 1: lab (ideas, research, debug logs)
  - Level 2: docs (PRDs, ADRs, specifications)
  - Level 3: audit (changelogs, completion reports)
  - Level 4: kb (retrospectives, knowledge extracts)
- `DocLayer` type is: `{ level: 0 | 1 | 2 | 3 | 4; label: string }`
- `DocStatusBadge` Vue component renders per-layer visual badges

### E1.3: Document Index Views

As a consumer, I can browse documents by category without knowing individual file paths.

**Acceptance Criteria:**
- `/index/` has sub-routes: `raw-all`, `planning`, `specs`, `research`, `worklogs`, `other`
- Each sub-route renders a curated document listing with links
- `/views/` directory contains changelog, commits, and WBS views

---

## E2: @phenotype/docs Shared Package

### E2.1: Config Factory (`createPhenotypeConfig`)

As a project maintainer, I can call `createPhenotypeConfig(options)` to get a fully-formed VitePress config with Phenotype defaults applied.

**Acceptance Criteria:**
- `createPhenotypeConfig` exported from `@phenotype/docs/config`
- `ConfigOptions` accepts: `title`, `description`, `base?`, `srcDir?`, `githubOrg?`, `githubRepo?`, `nav?`, `sidebar?`, `overrides?`
- Defaults: `base='/'`, `srcDir='docs'`, `githubOrg='KooshaPari'`, `lang='en-US'`
- Automatically infers `githubRepo` from `title.toLowerCase().replace(/\s+/g, '-')` when omitted
- Applied defaults: `lastUpdated: true`, `cleanUrls: true`, markdown line numbers, `github-light`/`github-dark` themes, local search, edit link pattern, outline `[2,3]`, external link icons
- Consumer `overrides` deep-merged on top via `deepMerge` (arrays concatenated)
- Return type: `ReturnType<typeof defineConfig>`

### E2.2: Sidebar Auto-Generator (`generateSidebar`)

As a project maintainer, I can call `generateSidebar({ srcDir, prefix, capitalizeGroups? })` to auto-generate a VitePress sidebar from a directory tree.

**Acceptance Criteria:**
- `generateSidebar` exported from `@phenotype/docs/utils`
- Traverses `join(srcDir, prefix)` recursively; returns `DefaultTheme.SidebarItem[]`
- `index.md` at each level maps to `{ text: 'Overview', link: '<prefix>/' }` placed first
- Subdirectories become collapsible groups (`collapsed: true`) with children recursed
- Other `.md` files become link items; base name is title-cased with hyphens replaced by spaces
- `capitalizeGroups` (default `true`) controls group label casing
- Returns `[]` gracefully when the directory does not exist

### E2.3: Deep-Merge Utility (`deepMerge`)

As a config builder, I can deep-merge two plain objects where arrays concatenate and nested objects recurse.

**Acceptance Criteria:**
- `deepMerge<T>(target, source)` exported from `@phenotype/docs/utils`
- Primitive `source` values override `target` values
- Arrays: `[...target, ...source]`
- Nested objects: recurse
- Neither input is mutated (spread into new object)

### E2.4: Vue Component Library (21 components)

As a documentation author, I can use 21 pre-registered Vue components in any VitePress project that imports the `@phenotype/docs` theme.

**Acceptance Criteria:**
- Theme entry (`@phenotype/docs/theme`) registers all components globally via `app.component(name, component)` in `enhanceApp`
- Registered components: `AuditTimeline`, `BackToTop`, `Breadcrumb`, `Callout`, `CategorySwitcher`, `CodeAnnotation`, `CodePlayground`, `ContentTabs`, `DemoGif`, `DocStatusBadge`, `KBGraph`, `LoadingSpinner`, `ModuleSwitcher`, `NavTabs`, `OpenAPI`, `StickyHeader`, `StickySidebar`, `Toast`, `ToastContainer`, `Tooltip`, `CommitLog`
- Custom CSS (`custom.css`) imports `@phenotype/design/css/vitepress-theme.css`; phenodocs-specific overrides only
- All components are also exported as named exports for selective import

### E2.5: Package Publishing

As a downstream Phenotype project, I can install `@phenotype/docs` from GitHub Packages.

**Acceptance Criteria:**
- Package name: `@phenotype/docs`; registry: `https://npm.pkg.github.com`; access: `public`
- Export map in `packages/docs/package.json`: `./theme`, `./config`, `./utils`, `./types`, `./css/custom.css` (keycap tokens via `@phenotype/design`)
- Workspace dependency in hub: `"@phenotype/docs": "workspace:*"`
- CI publishes on release tags

---

## E3: Site Quality and Tooling

### E3.1: Type Safety

As a contributor, `bun run typecheck` (vue-tsc) exits 0 on a clean tree.

**Acceptance Criteria:**
- `tsconfig.json` at workspace root covers `packages/docs/src/**` and `.vitepress/**`
- `vue-tsc --noEmit -p tsconfig.json` exits 0
- No implicit `any` in exported types

### E3.2: Lint Compliance

As a contributor, `bun run lint:ts` (oxlint) and `bun run lint` (markdownlint) exit 0 on a clean tree.

**Acceptance Criteria:**
- `oxlint.json` governs `.vitepress/` TypeScript
- `markdownlint-cli` governs `docs/**/*.md`
- Both exit 0 on a clean tree

### E3.3: Link Validity Check

As a maintainer, internal broken links are detected via `bun run check-links`.

**Acceptance Criteria:**
- `scripts/check_docs_links.py` runs via `uv run python`
- Exits 0 for a valid tree; exits non-zero and prints offending links on failure
- Called as part of `bun run check`

### E3.4: GitHub Pages Deployment

As a reader, the production site is live at `https://kooshapari.github.io/phenodocs/`.

**Acceptance Criteria:**
- GitHub Actions `deploy.yml` workflow triggers on merge to `main`
- Build command: `bun run build`; artifacts: `docs/.vitepress/dist/`
- Deployed to GitHub Pages with automatic HTTPS

---

## Out of Scope (v1)

- Server-side rendering or dynamic API endpoints
- Real-time collaborative editing
- Authentication / access control on the documentation site
- Paid hosting beyond GitHub Pages
