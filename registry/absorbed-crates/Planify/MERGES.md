# MERGES — Planify Consolidation Log

This document records every source that contributed code or content to Planify.

## Sources

| Source | What was taken | Where it lives in Planify |
| --- | --- | --- |
| `makeplane/plane` (preview branch, v1.3.1, AGPL-3.0) | Full pnpm monorepo: apps (admin/api/live/proxy/space/web), packages (codemods/constants/decorators/editor/hooks/i18n/logger/propel/services/shared-state/tailwind-config/types/typescript-config/ui/utils), deployments, docs, root config files | `upstream/` (entire upstream tree, unmodified) |
| `KooshaPari/Planify` (initial stub) | README and UPSTREAM.md scaffolding notes | `README.md` (root), `UPSTREAM.md` (root) |
| `KooshaPari/AgilePlus` (`docker-compose.plane.yml`) | Canonical compose for Plane stack (Postgres + Dragonfly + plane-api/worker/beat + plane-web) | `infra/docker-compose.plane.yml` |
| `KooshaPari/pheno` (`docker-compose.plane.yml` symlink target) | Confirms canonical compose lives in AgilePlus — same content, link only | (no copy — kept in AgilePlus) |
| `phenotype-landing/sites/*-landing` (Astro + Bun + Tailwind pattern) | Site scaffolding pattern (header / hero / feature grid / CTA / footer, dark slate theme) | `site/` (Astro + Bun + Tailwind, no Vue per match-org-pattern) |
| `KooshaPari/Planify` GitHub description | "Consolidated Plane.so fork — Phenotype PM frontend" | `README.md` (root) |

## Sources searched but NOT found

These were searched for during the inventory pass and yielded no usable content:

- `.glb` keyboard model (referenced by recon as a known visual element)
  - Searched: `/Users/kooshapari/CodeProjects/Phenotype/**/*.glb`
  - Result: zero matches
  - Status: missing asset. The landing site has a placeholder 3D scene that surfaces this gap
- `planify-site` sibling directory
  - Searched: `/Users/kooshapari/CodeProjects/Phenotype/repos/planify-site*`
  - Result: zero matches
  - Status: site scaffolded into `planify-wt/site/` instead of as a sibling
- Additional KooshaPari plane-so forks beyond `Planify`
  - Searched: `gh repo list KooshaPari --limit 500` filtered by `plane|planify|openplane|openspace|spaces`
  - Result: only `Planify` matches; `AgilePlus` is the Rust PM backend, not a Plane fork
- Local plane source clones
  - Searched: every `Planify/` directory under `repos/`
  - Result: all 6 are empty submodule slots; no plane source content

## How to use this repo

```bash
cd upstream
pnpm install
pnpm dev          # full Plane stack (apps/web, apps/space, apps/admin)
pnpm build        # turbo build

cd ../site
bun install
bun run dev       # planify.space landing
```

The `upstream/` directory is a verbatim copy of `makeplane/plane@preview` (v1.3.1)
plus the canonical `docker-compose.plane.yml` mirrored from `AgilePlus`.
Any customization by Phenotype should land OUTSIDE `upstream/`.

## Upstream sync

```bash
cd upstream
git remote add upstream https://github.com/makeplane/plane.git
git fetch upstream preview
git merge upstream/preview
```

## Attribution

- Plane (upstream) — AGPL-3.0 — © makeplane/plane contributors. See `upstream/LICENSE.txt` and `upstream/COPYRIGHT.txt`.
- Planify (this fork) — same AGPL-3.0 license inherited from upstream.