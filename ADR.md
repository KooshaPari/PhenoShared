# Architecture Decision Records -- phenodocs

**Version:** 1.1
**Date:** 2026-03-26

---

## ADR-001: VitePress as Documentation Engine

**Status:** Accepted
**Date:** 2026-03-26

**Context:**
The Phenotype organization needs a fast, Markdown-first static site generator that supports Vue components, full-text search, dark/light theming, and clean URL generation. The generator must produce a completely static output deployable to GitHub Pages without a server.

**Decision:**
Use VitePress 1.x as the documentation engine for both the federation hub and the `@phenotype/docs` shared package.

**Rationale (from actual config):**
- `defineConfig` and `DefaultTheme` APIs enable strongly typed configuration with TypeScript
- Built-in `provider: 'local'` search requires no external service
- `cleanUrls: true` and `lastUpdated: true` are first-class VitePress features used in production config
- Vue 3 SFCs (`.vue`) integrate natively as VitePress theme components
- Markdown line numbers and dual code theme (`github-light`/`github-dark`) are built-in

**Alternatives Considered:**
- **Docusaurus** — React-based, heavier bundle, incompatible with Vue SFC component approach
- **MkDocs** — Python runtime, less extensible for custom Vue components
- **Astro** — More flexible but higher configuration burden; VitePress is purpose-built for docs

**Consequences:**
- Node.js (>=20) and Bun are required build-time dependencies
- All custom components must be Vue 3 SFCs (21 components in `packages/docs/src/theme/components/`)
- `vue-tsc` is required for type-checking `.vue` files alongside TypeScript

---

## ADR-002: Bun as Package Manager and Script Runner

**Status:** Accepted
**Date:** 2026-03-26

**Context:**
The project needs a fast package manager compatible with npm workspaces for the `packages/docs` sub-package. Speed of `bun install` matters for CI.

**Decision:**
Use Bun 1.x (`packageManager: "bun@1.3.10"` in `package.json`) for dependency installation and script execution.

**Rationale:**
- `bun.lock` is present at repo root; `packageManager` field enforces Bun
- `workspace:*` protocol in `package.json` is natively supported by Bun
- `bun run dev/build/preview/check` matches existing scripts
- `bun run typecheck` invokes `vue-tsc` which is a devDependency installed by Bun

**Alternatives Considered:**
- **pnpm** — Also supports `workspace:*`; no compelling reason to change given existing Bun lockfile
- **npm** — No native workspace hoisting; slower

**Consequences:**
- CI and local dev environments must have Bun installed
- Python tooling (`uv`, `pyproject.toml`) runs in parallel via `uv run` for `scripts/check_docs_links.py`

---

## ADR-003: @phenotype/docs as a Separate Publishable Workspace Package

**Status:** Accepted
**Date:** 2026-03-26

**Context:**
The VitePress theme, config factory, sidebar generator, deep-merge utility, and Vue components need to be reusable across all Phenotype project documentation sites without copy-paste.

**Decision:**
Extract the shared layer into a workspace package at `packages/docs` with package name `@phenotype/docs`, published to GitHub Packages (`npm.pkg.github.com`). The hub consumes it as `"@phenotype/docs": "workspace:*"`.

**Rationale (from actual code):**
- `packages/docs/package.json` defines `"name": "@phenotype/docs"` and `"private": false`
- Export map exposes five entry points: `./theme`, `./config`, `./utils`, `./types`, `./css/custom.css`
- Keycap palette and VitePress theme CSS come from `@phenotype/design` (`KooshaPari/phenoDesign`); phenodocs does not fork design tokens
- `publishConfig.registry: "https://npm.pkg.github.com"` is set
- `createPhenotypeConfig` in `./config` calls `deepMerge` from `./utils` — intra-package, type-safe

**Alternatives Considered:**
- **Inline in hub** — Zero reuse; other Phenotype projects cannot adopt consistent theme
- **Separate git repo** — Heavier release cycle; workspace reference more convenient during development

**Consequences:**
- Downstream projects need `.npmrc` with `@phenotype:registry=https://npm.pkg.github.com` and a GitHub Packages auth token
- Breaking changes to config API require a semver bump
- All 21 Vue components must be maintained in this package

---

## ADR-004: TypeScript-First Config with deepMerge Override Pattern

**Status:** Accepted
**Date:** 2026-03-26

**Context:**
VitePress config can be complex. Consumers need to extend Phenotype defaults without rewriting them. Simple `Object.assign` loses nested structure; JSON merge patches are not type-safe.

**Decision:**
Implement `deepMerge<T>(target, source)` in `packages/docs/src/utils/config-merger.ts` and use it in `createPhenotypeConfig` to merge consumer `overrides` on top of the base config. Arrays are concatenated; nested objects are recursed; primitives override.

**Rationale:**
- `deepMerge` is ~30 lines, zero dependencies, fully typed
- `createPhenotypeConfig` returns `ReturnType<typeof defineConfig>` — consumers get exact VitePress type inference
- Pattern is auditable and avoids hidden magic (no Proxy, no `lodash.merge`)

**Alternatives Considered:**
- **lodash.merge** — Extra dependency; `lodash` is not in the lockfile
- **Spread-only** — Loses nested config structure (e.g. `themeConfig.sidebar` would be replaced, not merged)
- **Custom DSL** — Unnecessary complexity for a static config

**Consequences:**
- `deepMerge` must handle all VitePress config shapes (plain objects and arrays only — no class instances)
- Test coverage for `deepMerge` edge cases is important to prevent silent config override bugs

---

## ADR-005: Filesystem-Driven Sidebar Generation

**Status:** Accepted
**Date:** 2026-03-26

**Context:**
Documentation sections grow over time. Maintaining sidebar configuration by hand leads to drift between the filesystem and the nav tree. A convention-based auto-generator reduces maintenance burden.

**Decision:**
Implement `generateSidebar({ srcDir, prefix, capitalizeGroups? })` in `packages/docs/src/utils/sidebar-generator.ts`. It reads the filesystem at build time via `readdirSync`/`statSync` and produces `DefaultTheme.SidebarItem[]`.

**Rationale (from actual code):**
- `index.md` → placed first as `{ text: 'Overview', link: '<prefix>/' }` — standard convention
- Subdirectories → `{ text: label, collapsed: true, items: [...] }` — collapsible groups
- `.md` files → `{ text: titleCased, link: '<prefix>/<name>' }` — individual pages
- `capitalizeGroups` option (default `true`) — cosmetic control without re-implementing the traversal
- Returns `[]` gracefully on missing directories (try/catch around `readdirSync`)

**Alternatives Considered:**
- **VitePress `rewrites` + manual sidebar** — Error-prone; no single source of truth
- **vitepress-sidebar plugin** — External dependency; less control over layer-specific conventions

**Consequences:**
- Sidebar order is alphabetical by default; non-alphabetical ordering requires either filename prefixes or explicit overrides via `ConfigOptions.sidebar`
- Empty directories produce no sidebar items (correct behavior; enforced by `children.length > 0` check)

---

## ADR-006: Layered Content Architecture (0–4)

**Status:** Accepted
**Date:** 2026-03-26

**Context:**
The Phenotype documentation corpus spans ephemeral scratch notes, in-progress research, formal specifications, changelogs, and curated knowledge. A flat structure makes content discovery difficult for different audiences.

**Decision:**
Define five content layers encoded in `DocLayer.level: 0 | 1 | 2 | 3 | 4` (typed in `packages/docs/src/types/index.ts`). Map to directory views: lab (`/views/`), docs (`/index/specs`), audit (`/index/worklogs`), kb. The `DocStatusBadge` component renders per-layer visual badges.

**Rationale:**
- Five discrete levels rather than free-form tags — enables consistent badge styling by numeric level
- Layers map to the Document Index sub-routes already implemented: `planning`, `specs`, `research`, `worklogs`, `other`
- `DocLayer` type in `@phenotype/docs/types` ensures all consumers use the same schema

**Alternatives Considered:**
- **Free-form frontmatter tags** — No schema enforcement; inconsistent UI rendering
- **Separate VitePress sites per layer** — Fragmented search; no unified navigation

**Consequences:**
- All Phenotype documentation authors must understand layer semantics before tagging content
- Level 0 (ephemeral) is internal-only and should not appear in the deployed site's public navigation
