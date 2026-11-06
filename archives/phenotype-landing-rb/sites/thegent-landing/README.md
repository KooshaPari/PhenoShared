# thegent-landing

[![AI Slop Inside](https://sladge.net/badge.svg)](https://sladge.net)

Production landing page at `thegent.kooshapari.com` for [KooshaPari/thegent](https://github.com/KooshaPari/thegent), the Python agent runtime and orchestration system in the Phenotype ecosystem.

## Purpose

`thegent-landing` is the Tier-2 brand surface for theGent. It gives the runtime a stable domain, pulls public project metadata at build time, and exposes path-based microfrontends for landing-site docs, QA, observability, and pull-request previews.

The site is also mirrored to GitHub Pages at `https://kooshapari.github.io/thegent-landing/`; links are generated through `src/lib/site.ts` so the Vercel custom-domain build and Pages base-path build both work.

## Architecture

- **Frontend:** Astro 6 static site
- **Styling:** Tailwind CSS 4 with Phenotype CSS tokens
- **Deployment:** Vercel plus GitHub Pages mirror
- **Domain:** `thegent.kooshapari.com` via Cloudflare CNAME
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

## Path Microfrontends

Per Phenotype org-pages policy, `thegent.kooshapari.com` hosts these surfaces:

| Path | Status | Purpose |
|------|--------|---------|
| `/` | Active | theGent overview, GitHub metadata, runtime proof panel |
| `/docs` | Active with fallback | Renders this landing repo's `docs/` tree from GitHub |
| `/otel` | Active, env-gated | Embeds a public PhenoObservability UI |
| `/qa` | Active with snapshot fallback | Shows landing-site coverage, lint, and FR trace reports |
| `/preview/<pr#>` | Active with fallback | Canonical static redirect pages for landing PR previews |

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
- Base-path URL helper: `src/lib/site.ts`
- Docs microfrontend: `src/pages/docs/[...slug].astro`
- OTel embed: `src/pages/otel/index.astro`
- QA dashboard: `src/pages/qa/index.astro`
- PR preview redirects: `src/pages/preview/[prNumber].astro`
- Shared design tokens: `src/styles/globals.css`

The shared visual base is GMK Arch teal (`#7ebab5`), aligned with the wider Phenotype landing-page family.

## Deployment

Vercel builds the custom-domain site from `main`.

```bash
vercel --prod
```

Cloudflare DNS should point:

```text
CNAME thegent -> cname.vercel-dns.com
```

The GitHub Pages mirror is built by `.github/workflows/pages.yml` with `GITHUB_PAGES=true`, which makes Astro emit URLs under `/thegent-landing/`.

## Related

- [theGent](https://github.com/KooshaPari/thegent)
- [projects.kooshapari.com](https://github.com/KooshaPari/portfolio)
- [Site infrastructure](docs/governance/site-infrastructure.md)
