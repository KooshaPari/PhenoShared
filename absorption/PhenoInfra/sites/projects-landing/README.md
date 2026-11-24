# projects-landing

Phenotype org portfolio — auto-generated landing page at <https://projects.kooshapari.com>.

Static site listing all active KooshaPari / Phenotype org repositories with topic filters and search. Built with Astro 6 + Tailwind CSS 4. Deployed on Vercel with a GitHub Pages governance mirror.

## Stack

- **Framework**: Astro 6 (static, with light client-side islands for filter/search)
- **Styling**: Tailwind CSS 4 (`@tailwindcss/vite`) + impeccable CSS reset
- **Data**: `data/repos.json` snapshot from GitHub API (`scripts/fetch-repos.mjs`)
- **Deploy**: Vercel (static output, custom domain `projects.kooshapari.com`) plus GitHub Pages mirror

## Development

```bash
bun install
bun dev                 # http://localhost:4321
bun run build           # static output → dist/
bun run preview         # preview build
```

## Refresh repo data

```bash
bun run data:refresh        # node scripts/fetch-repos.mjs (uses GitHub REST API)
```

`data/repos.json` is also regenerated automatically on every Vercel build via the
`prebuild` hook (`node scripts/fetch-repos.mjs`). The committed snapshot is just a
fallback used during local dev or when the GitHub API is unreachable. The Node
fetcher honors `GITHUB_TOKEN`/`GH_TOKEN` if set (recommended on Vercel to lift the
60 req/hr unauth limit).

## Scheduled refresh (Vercel cron + deploy hook)

Nightly refresh runs on Vercel, while GitHub Pages stays in sync through the
`main`-branch Pages workflow mirror.

Mechanism (Option C — rebuild on a cron-triggered redeploy):

1. `vercel.json` declares a cron that hits `/api/cron-refresh` daily at 07:17 UTC.
2. `api/cron-refresh.ts` POSTs to the Vercel Deploy Hook URL stored in `VERCEL_DEPLOY_HOOK`.
3. Vercel kicks off a new production build; `prebuild` re-runs `scripts/fetch-repos.mjs` against the live GitHub API; `astro build` bakes the fresh data into static output.

One-time setup in the Vercel dashboard:

1. **Settings -> Git -> Deploy Hooks**: create a hook (name `cron-refresh`, branch `main`). Copy the URL.
2. **Settings -> Environment Variables**: add `VERCEL_DEPLOY_HOOK` = `<hook url>` (Production scope).
3. (Optional but recommended) Add `GITHUB_TOKEN` with `public_repo` scope so the build hits authenticated rate limits.

Hobby tier covers the daily cron; no paid integration required.

## Deploy

```bash
vercel link --yes               # first time only
vercel deploy --prod
```

Custom domain `projects.kooshapari.com` is wired via Cloudflare CNAME → `cname.vercel-dns.com` (record id `2ee0d797675e4fdc5fe5fcf37677fa2f`).

GitHub Pages deploys from `.github/workflows/pages.yml` as a static mirror of `dist/`.
It builds with `GITHUB_PAGES=true`, which sets Astro's base path to
`/projects-landing`. The mirror is updated on pushes to `main` and can also be
manually dispatched. It is not the canonical custom-domain route, but it must
stay build-clean for governance.

## Internal network options

The home page reveals local development portal links when the browser appears to
be on `localhost`, `127.0.0.1`, `.local`, `.ts.net`, `.tailnet`, or a
`100.64.0.0/10` Tailscale address. For local QA, append `?internal=1` or set
`localStorage.setItem("phenotype_internal", "1")`.

## Layout

- `src/pages/index.astro` — single page, renders all cards from `data/repos.json` at build time
- `src/pages/koosha.astro` — personal-level KooshaPari landing layer over the project graph
- `src/styles/globals.css` — Tailwind import + impeccable reset + theme tokens
- `scripts/fetch-repos.mjs` — refresh data snapshot (GitHub API)
- `data/repos.json` — committed snapshot (refreshed by hand or in CI)
- `vercel.json` — framework + build config
- `astro.config.mjs` — Astro + Tailwind Vite plugin

## Governance

Implements the Phenotype "Org Pages Default Expansion" standing policy: every project gets a portfolio entry here plus a `<project>.kooshapari.com` landing page with `/docs`, `/otel`, `/qa`, `/preview/<pr#>` path-based microfrontends.
