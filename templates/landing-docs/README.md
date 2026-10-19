# Landing + docs template

Static landing page and docs site (VitePress) with a compete/ section, deployed to GitHub Pages on the free tier. Public static content only: no private data, no tokens, no API calls.

Use in a repo:

1. Copy `docs/` and `.github/workflows/pages.yml` from this folder to the repo root. If the repo already has `docs/`, copy only `docs/.vitepress/`, `docs/index.md` (landing) and `docs/compete/`, and keep the existing pages.
2. `package.json`: if the repo has none, copy the template file as-is. If the repo already has one, merge instead of replacing - add the three scripts (`docs:dev`, `docs:build`, `docs:preview`) and the `vitepress` devDependency from the template into the existing manifest, and keep the repo's own dependencies, scripts, metadata and workspace config.
3. Edit `docs/.vitepress/config.mts`: set `title`, `description` and `base` (`/<repo>/` for the default github.io URL).
4. Edit the landing in `docs/index.md` and fill `docs/compete/index.md` with real competitor facts and sources.
5. Enable Pages (Settings, Pages, Source: GitHub Actions) and push to main. The workflow builds and deploys.

Done-proof for a repo: the commit on main, the Pages run link, and the live URL returning HTTP 200.

Placement rules: docs/landing may be public at `<project>.phenotype.space`; apps and backends never go on that host (see docs/governance/web-surface-rules.md).
