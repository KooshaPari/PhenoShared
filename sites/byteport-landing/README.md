# byteport-landing

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/KooshaPari/phenotype-landing/ci.yml?branch=main)](https://github.com/KooshaPari/phenotype-landing/actions)
[![TypeScript](https://img.shields.io/badge/typescript-5%2B-3178C6?logo=typescript)](https://www.typescriptlang.org/)

Production landing page at `byteport.kooshapari.com` for [KooshaPari/BytePort](https://github.com/KooshaPari/BytePort), a Rust-based project management and workflow orchestration platform. Part of the Phenotype org-pages architecture (Tier 2; Tier 1 is `projects.kooshapari.com`).

## Purpose

Provide a cohesive entry point to Byteport documentation, dashboards, and QA reports. The landing page dynamically pulls project metadata (README, latest release, stats) from the GitHub API at build time, avoiding stale content. Implements the Phenotype org-pages pattern with path-based microfrontends under a single domain.

## Architecture

- **Frontend:** Astro 5 (static HTML at build time, edge rendering)
- **Styling:** Tailwind CSS 4 with impeccable design baseline
- **Deployment:** Vercel (serverless functions for API routes)
- **Domain:** `byteport.kooshapari.com` via Cloudflare CNAME
- **Data sources:** GitHub API (README, releases), OpenTelemetry backend (metrics), local database (QA reports)

## Stack Details

```toml
# Runtime
astro = "5.0"
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
git clone https://github.com/KooshaPari/byteport-landing.git
cd byteport-landing

# Install dependencies
bun install

# Set environment variables
export GITHUB_TOKEN=ghp_xxxx  # Optional: higher API rate limits
export VERCEL_ENV=development

# Start dev server (with HMR + auto-reload)
bun run dev
# Server: http://localhost:3000
```

### Build for Production

```bash
# Build static site
bun run build

# Preview production build locally
bun run preview

# Deploy to Vercel
bun run deploy
```

## Path Microfrontends

Per Phenotype org-pages standing policy, `byteport.kooshapari.com` hosts multiple surfaces as path-based microfrontends:

| Path | Component | Status | Purpose |
|------|-----------|--------|---------|
| `/` | Landing page | ✅ Active | Byteport overview, GitHub metadata, CTA |
| `/docs` | VitePress | 📋 Planned | Mounted docs from Byteport/docs @ `/docs` |
| `/otel` | OTEL Dashboard | 📋 Planned | Observability metrics (latency, throughput, errors) |
| `/qa` | QA Reports | 📋 Planned | Test coverage, Semgrep results, security scans |
| `/preview/<pr#>` | PR Preview | 📋 Planned | Deploy PR previews to `/preview/123` on merge to staging |

### Implementing Microfrontends

Each microfrontend is isolated and mounted independently:

```astro
<!-- src/pages/docs/[...slug].astro — VitePress passthrough -->
---
import { getVitePressPage } from '../integrations/vitepresse';

const doc = await getVitePressPage(Astro.params.slug);
---
<div set:html={doc.html} />
```

## Environment Variables

```bash
# GitHub API (optional, but recommended)
GITHUB_TOKEN=ghp_xxxx           # Increases rate limit to 5000 req/hr

# Vercel deployment
VERCEL_ENV=production|staging    # Set by Vercel automatically
VERCEL_URL=byteport.kooshapari.com

# OTEL backend (when microfrontend launches)
OTEL_ENDPOINT=https://otel.internal/api/v1
OTEL_AUTH_TOKEN=xxx
```

## Building & Customization

### Modify Landing Page Content

Edit `src/components/Hero.astro`, `src/components/Features.astro`:

```astro
---
// src/components/Hero.astro
const githubData = await fetchGitHubRepo('KooshaPari/BytePort');
---

<section class="hero">
  <h1>{githubData.description}</h1>
  <p>Latest release: {githubData.latestTag}</p>
</section>
```

### Add Custom Styling

Extend Tailwind in `tailwind.config.ts`:

```ts
export default {
  theme: {
    extend: {
      colors: {
        'phenotype-purple': '#7c3aed',
      },
    },
  },
}
```

### Fetch Live Data at Build Time

```astro
---
// src/pages/index.astro
import { getGitHubREADME, getLatestRelease } from '../lib/github';

const readme = await getGitHubREADME('KooshaPari/BytePort');
const release = await getLatestRelease('KooshaPari/BytePort');
---

<article set:html={readme.html} />
<p>Latest: {release.tag_name}</p>
```

## Testing & Verification

```bash
# Lint and format
bun run lint
bun run format

# Type check (Astro)
astro check

# Build and verify no errors
bun run build

# Test in browser
bun run preview
# Visit http://localhost:3000 manually
```

## Deployment

### Automated (Push to main)

```yaml
# .github/workflows/deploy.yml triggers on:
# - Push to main
# - Manual trigger via workflow_dispatch

# 1. Install dependencies
# 2. Build static site
# 3. Deploy to Vercel (automatic with linked repo)
```

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
CNAME agileplus → cname.vercel-dns.com

# Verify
nslookup byteport.kooshapari.com
# Should resolve to Vercel IP
```

## Governance

- **Codebase:** TypeScript/Astro (no server-side logic; all static/edge)
- **Styling:** Tailwind 4 + impeccable CSS baseline
- **Updates:** Dependabot auto-updates dev dependencies; manual review for breaking changes
- **Monitoring:** Error tracking via Sentry (optional)
- **Deployment:** Vercel auto-deploys on push; no manual CI needed

## Related

- [Byteport](https://github.com/KooshaPari/BytePort) — Main project repository
- [projects.kooshapari.com](https://github.com/KooshaPari/portfolio) — Tier 1 landing (all projects)
- [phenotype-design](../phenotype-design/) — Design system & components
- [Org Pages Architecture](https://github.com/KooshaPari/phenotype-infrakit/docs/governance/org-pages-architecture.md)
