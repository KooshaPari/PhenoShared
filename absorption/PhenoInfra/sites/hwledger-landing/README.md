# hwledger-landing

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/KooshaPari/phenotype-landing/ci.yml?branch=main)](https://github.com/KooshaPari/phenotype-landing/actions)
[![TypeScript](https://img.shields.io/badge/typescript-5%2B-3178C6?logo=typescript)](https://www.typescriptlang.org/)

Production landing page at `hwledger.kooshapari.com` for [KooshaPari/hwLedger](https://github.com/KooshaPari/hwLedger), an LLM capacity planner, fleet ledger, and desktop inference runtime. Part of the Phenotype org-pages architecture (Tier 2; Tier 1 is `projects.kooshapari.com`).

## Purpose

Provide a cohesive entry point to Hwledger documentation, dashboards, and QA reports. The landing page dynamically pulls project metadata (README, latest release, stats) from the GitHub API at build time, avoiding stale content. Implements the Phenotype org-pages pattern with path-based microfrontends under a single domain.

## Architecture

- **Frontend:** Astro 6 (static HTML at build time)
- **Styling:** Tailwind CSS 4 with impeccable design baseline
- **Deployment:** Vercel plus a GitHub Pages mirror
- **Domain:** `hwledger.kooshapari.com` via Cloudflare CNAME
- **Data sources:** GitHub API (README, releases), PhenoObservability UI, QA JSON reports

## Stack Details

```toml
# Runtime
astro = "6.0"
tailwindcss = "4.0"

# Build-time
octokit = "^21.0"  # GitHub API client
serde = { version = "1.0", features = ["derive"] }
tokio = { version = "1.0", features = ["full"] }

# Optional: async operations
@vercel/og = "^0.6"  # Open Graph image generation
```

## Local Development

### Prerequisites

- `bun` 1.0+ (package manager & runtime)
- Node.js 20+ (fallback)
- `git` (for GitHub metadata fetching during build)

### Setup & Run

```bash
# Clone repository
git clone https://github.com/KooshaPari/phenotype-landing.git
cd phenotype-landing/sites/hwledger-landing

# Install dependencies
bun install

# Set environment variables
export GITHUB_TOKEN=ghp_xxxx  # Optional: higher API rate limits
export VERCEL_ENV=development

# Start dev server (with HMR + auto-reload)
bun run dev
# Server: http://localhost:4321
```

### Build for Production

```bash
# Build static site
bun run build

# Build the GitHub Pages mirror
GITHUB_PAGES=true bun run build

# Preview production build locally
bun run preview

# Deploy to Vercel
vercel --prod
```

## Path Microfrontends

Per Phenotype org-pages standing policy, `hwledger.kooshapari.com` hosts multiple surfaces as path-based microfrontends:

| Path | Component | Status | Purpose |
|------|-----------|--------|---------|
| `/` | Landing page | ✅ Active | Hwledger overview, GitHub metadata, CTA |
| `/docs` | Docs browser | Active | Renders hwLedger `docs/` from GitHub |
| `/otel` | OTel Dashboard | Active fallback | Embeds PhenoObservability when configured |
| `/qa` | QA Reports | Active fallback | Test coverage, lint, and FR traceability snapshots |
| `/preview/<pr#>` | PR Preview | Active fallback | Stable PR preview redirects when open PRs exist |

### Implementing Microfrontends

Each microfrontend is isolated and mounted independently. The `/docs` route is the
GitHub-backed docs browser in `src/pages/docs/[...slug].astro`; it walks the
`docs/` tree from the `KooshaPari/hwLedger` repo and renders markdown from the
GitHub Contents API.

```astro
<!-- src/pages/docs/[...slug].astro — GitHub-backed docs browser -->
---
const listing = await ghJson(`repos/${REPO}/contents/${path}?ref=main`);
---
<div set:html={bodyHtml} />
```

## Environment Variables

```bash
# GitHub API (optional, but recommended)
GITHUB_TOKEN=ghp_xxxx           # Increases rate limit to 5000 req/hr

# Vercel deployment
VERCEL_ENV=production|staging    # Set by Vercel automatically
VERCEL_URL=hwledger.kooshapari.com

# OTel UI embed
PHENO_OTLP_UI_URL=https://observability.example.com
PHENO_OBSERVABILITY_UI_URL=https://observability.example.com
```

## Building & Customization

### Modify Landing Page Content

Edit `src/pages/index.astro`:

```astro
---
// src/pages/index.astro
const REPO = "KooshaPari/hwLedger";
---

<section class="hero">
  <h1>hwLedger</h1>
  <p>{PAGE_DESCRIPTION}</p>
</section>
```

### Add Custom Styling

Shared color tokens live in `src/styles/globals.css`. hwLedger uses the
Phenotype GMK Arch teal accent (`#7ebab5`) for consistency with the project hub.

### Fetch Live Data at Build Time

The landing page uses server-side data fetching via Astro's `getStaticPaths` and direct API calls.
Refer to `src/pages/index.astro` for the current implementation of GitHub metadata fetching.

## Testing & Verification

```bash
# Type check (Astro)
bunx astro check

# Build and verify no errors
bun run build

# Test in browser
bun run preview
# Visit http://localhost:4321 manually
```

## Deployment

### Automated Workflows

- `.github/workflows/ci.yml` runs on pushes and pull requests to `main`. It
  installs dependencies, runs `bunx astro check`, and builds the site.
- `.github/workflows/pages.yml` runs on pushes to `main` and manual
  `workflow_dispatch`. It builds with `GITHUB_PAGES=true` and publishes the
  `dist/` artifact to GitHub Pages.

### Manual Deployment

```bash
# Deploy to production
vercel --prod

# Deploy to staging
vercel --target staging
```

### Custom Domain (Cloudflare)

```bash
# In Cloudflare DNS:
CNAME hwledger → cname.vercel-dns.com

# Verify
nslookup hwledger.kooshapari.com
# Should resolve to Vercel IP
```

## Governance

- **Codebase:** TypeScript/Astro (no server-side logic; all static/edge)
- **Styling:** Tailwind 4 + impeccable CSS baseline
- **Updates:** Dependabot auto-updates dev dependencies; manual review for breaking changes
- **Monitoring:** Error tracking via Sentry (optional)
- **Deployment:** Vercel auto-deploys on push; no manual CI needed

## Related

- [Hwledger](https://github.com/KooshaPari/hwLedger) — Main project repository
- [projects.kooshapari.com](https://github.com/KooshaPari/portfolio) — Tier 1 landing (all projects)
- [phenotype-design](../phenotype-design/) — Design system & components
- [Org Pages Architecture](https://github.com/KooshaPari/phenotype-infrakit/docs/governance/org-pages-architecture.md)
