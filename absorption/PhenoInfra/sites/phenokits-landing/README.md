# phenokits-landing

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/KooshaPari/phenotype-landing/ci.yml?branch=main)](https://github.com/KooshaPari/phenotype-landing/actions)
[![TypeScript](https://img.shields.io/badge/typescript-5%2B-3178C6?logo=typescript)](https://www.typescriptlang.org/)

Production landing page at `phenokits.kooshapari.com` for [KooshaPari/PhenoKits](https://github.com/KooshaPari/PhenoKits), the reusable kit catalog for Phenotype templates, libraries, governance assets, and integration adapters.

## Purpose

PhenoKits is a Tier-2 Phenotype brand surface. It gives the kit catalog a stable domain, pulls public GitHub metadata at build time, and exposes path-based microfrontends for docs, QA, observability, and pull-request previews.

## Architecture

- **Frontend:** Astro 6 static site
- **Styling:** Tailwind CSS 4 with Phenotype CSS tokens
- **Deployment:** Vercel plus a GitHub Pages mirror
- **Domain:** `phenokits.kooshapari.com` via Cloudflare CNAME
- **Data sources:** GitHub API, committed QA snapshots, PhenoObservability UI

## Local Development

### Prerequisites

- `bun` 1.0+
- Node.js 20+
- `git`

### Setup

```bash
bun install
cp .env.example .env
bun run dev
```

Local dev serves at `http://localhost:4321`.

### Build

```bash
bunx astro check
bun run build
bun run preview
```

For the GitHub Pages mirror, build with `GITHUB_PAGES=true bun run build`.

## Path Microfrontends

Per Phenotype org-pages policy, `phenokits.kooshapari.com` hosts these surfaces:

| Path | Status | Purpose |
|------|--------|---------|
| `/` | Active | PhenoKits overview, GitHub metadata, brand proof panel |
| `/docs` | Active with fallback | Renders the source repo `docs/` tree from GitHub |
| `/otel` | Active, env-gated | Embeds a public PhenoObservability UI |
| `/qa` | Active with snapshot fallback | Shows coverage, lint, and FR trace reports |
| `/preview/<pr#>` | Active with fallback | Canonical static redirect pages for PR previews |

## Environment Variables

```bash
# GitHub API, optional but recommended for build-time rate limits.
GITHUB_TOKEN=

# Observability iframe source for /otel.
PHENO_OTLP_UI_URL=

# Accepted alias for the same public PhenoObservability UI.
PHENO_OBSERVABILITY_UI_URL=
```

## Editing

- Main landing content: `src/pages/index.astro`
- Docs microfrontend: `src/pages/docs/[...slug].astro`
- OTel embed: `src/pages/otel/index.astro`
- QA dashboard: `src/pages/qa/index.astro`
- PR preview redirects: `src/pages/preview/[prNumber].astro`
- Shared design tokens: `src/styles/globals.css`

The current accent uses a GMK Arch inspired teal (`#7ebab5`) aligned with the wider Phenotype landing-page family.

## Deployment

Vercel builds the static site from `main`.

```bash
vercel --prod
```

Cloudflare DNS should point:

```text
CNAME phenokits -> cname.vercel-dns.com
```

## Related

- [PhenoKits](https://github.com/KooshaPari/PhenoKits)
- [projects.kooshapari.com](https://github.com/KooshaPari/portfolio)
- [Org Pages Architecture](https://github.com/KooshaPari/phenotype-infrakit/docs/governance/org-pages-architecture.md)
