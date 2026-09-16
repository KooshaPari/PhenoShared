# Planify

**Phenotype PM Web Frontend** — Consolidated Plane.so fork

Planify is the web-based project management UI for the Phenotype platform, derived from [Plane](https://github.com/makeplane/plane). It powers the AgilePlus dashboard and integrates with the Phenotype ecosystem.

## Layout

```
planify/
├── upstream/                 # Verbatim seed from makeplane/plane@preview (v1.3.1, AGPL-3.0)
│   ├── apps/                 # admin, api, live, proxy, space, web
│   ├── packages/             # 15 shared TS packages
│   ├── deployments/          # Helm + Docker manifests
│   ├── docs/                 # Architecture + module docs
│   ├── package.json          # pnpm workspace root
│   ├── pnpm-workspace.yaml
│   ├── pnpm-lock.yaml
│   ├── turbo.json
│   └── LICENSE.txt           # AGPL-3.0 inherited from upstream
├── site/                     # planify.space landing page (Astro + Bun + Tailwind)
├── infra/                    # Phenotype-specific infra additions
├── UPSTREAM.md               # Original seeding notes
└── MERGES.md                 # Consolidation provenance
```

## Status

- DONE: `upstream/` seeded with verbatim snapshot of `makeplane/plane@preview` v1.3.1
- DONE: `infra/docker-compose.plane.yml` mirrors canonical compose from AgilePlus
- DONE: `site/` scaffolded with Astro + Bun + Tailwind (matches sibling Phenotype landings)
- WARNING: `.glb` keyboard model missing on disk — site has placeholder + TODO marker
- SKIPPED: `pnpm install` and `bun install` deferred due to disk pressure (42 GiB free)

### CI/CD

![CI](https://github.com/KooshaPari/Planify/actions/workflows/ci.yml/badge.svg)
![License](https://img.shields.io/github/license/KooshaPari/Planify)

GitHub Actions CI runs on every push and pull request to `main`, with two
parallel jobs:

- **Site build** — type-checks and builds the Astro landing page (`site/`)
- **Upstream check** — runs pnpm checks on the Plane.so fork (`upstream/`)

An automated upstream-sync workflow runs weekly to pull changes from
`makeplane/plane`, and Dependabot auto-merges patch-level npm dependency
updates.

## Deployment

- Web: Vercel (planify.space or planify.kooshapari.com)
- Stack: Upstream Plane (apps/web, apps/space, apps/admin)
- DB/cache: Postgres 16 + Dragonfly via infra/docker-compose.plane.yml

## Architecture

Planify is the web frontend counterpart to AgilePlus (Rust backend PM substrate).
- Dashboard UI (Planify apps/web)
- Workspace UI (Planify apps/space)
- Admin UI (Planify apps/admin)
- Backend API & storage (AgilePlus)
- Shared domain models (phenotype-domain SDKs)

## Quick start

```
# 1. Run upstream Plane stack
cd upstream && pnpm install && pnpm dev

# 2. Or Phenotype-infra compose
cd ../infra && docker compose -f docker-compose.plane.yml up -d

# 3. Build landing site
cd ../site && bun install && bun run dev
```

## Links

- Upstream: https://github.com/makeplane/plane
- AgilePlus: https://github.com/KooshaPari/AgilePlus
- phenotype-landing: https://github.com/KooshaPari/phenotype-landing
