# Pages deploy fix for phenotype-landing

## Status: draft 2026-06-09

## Diagnosis

- 6 Astro/Bun static landing sites in sites/* are built by ci.yml matrix (agileplus, byteport, hwledger, phenokits, projects, thegent). `sites/odin-landing` exists on disk but is not in the build matrix.
- ci.yml runs `bun install`, `bunx astro check`, `bun run build` per site — no `actions/deploy-pages` or `actions/upload-pages-artifact` step.
- Repo has no `.github/workflows/deploy.yml` and no `gh-pages` / `pages` branch; Pages is not enabled in repo settings.
- Result: `username.github.io/phenotype-landing/` (or any Pages URL) 404s — no artifact ever published.

## Fix options

A. Enable GitHub Pages for the canonical landing site (e.g. sites/main-landing)
B. Move all 6 sites to a separate repo per site
C. Use Vercel/Netlify for the multi-site deployment

## Test plan

- Pick option A (lowest effort): enable Pages for sites/main-landing
- Add per-site Vitepress/Astro Pages workflow
