# projects-landing — AGENTS.md

## Status

**ACTIVE** — Phenotype org portfolio site (projects.kooshapari.com)

## Repository

- **Owner**: Phenotype org / KooshaPari
- **Stack**: Astro 6, Bun, TypeScript, Tailwind
- **Data**: GitHub API (not `gh CLI`)
- **CI**: GitHub Actions build + Vercel deploy
- **Cron**: Daily refresh via `api/cron-refresh.ts` + Vercel deploy hook
- **License**: MIT

## Agent Rules

- The `data/repos.json` is build-time generated from `scripts/fetch-repos.mjs`.
- Do NOT use `gh CLI` in this repo — the GitHub API is the canonical source.
- The `fetch-repos.sh` shell script has been removed; use `bun run data:refresh`.
- Run `bunx astro check` and `bun run build` before committing.
- Follow the `Taskfile.yml` SSOT recipes for quality gates.

## Quick Start

```bash
bun install
bun run data:refresh   # fetch fresh GitHub data
bun run check          # astro typecheck
bun run build          # build static site
```

## Data Refresh

```bash
# Manual refresh (uses GITHUB_TOKEN env)
bun run data:refresh

# CI refresh (triggered by cron-refresh.ts)
# Vercel deploy hook re-runs prebuild automatically
```