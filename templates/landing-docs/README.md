# Landing + docs template

Static landing page and docs site (VitePress) with a compete/ section, deployed to GitHub Pages on the free tier. Public static content only: no private data, no tokens, no API calls.

Use in a repo:

1. Copy `docs/`, `package.json` and `.github/workflows/pages.yml` from this folder to the repo root. If the repo already has `docs/`, copy only `docs/.vitepress/`, `docs/index.md` (landing) and `docs/compete/`, and keep the existing pages.
2. Edit `docs/.vitepress/config.mts`: set `title`, `description` and `base` (`/<repo>/` for the default github.io URL).
3. Edit the landing in `docs/index.md` and fill `docs/compete/index.md` with real competitor facts and sources.
4. Enable Pages (Settings, Pages, Source: GitHub Actions) and push to main. The workflow builds and deploys.

Done-proof for a repo: the commit on main, the Pages run link, and the live URL returning HTTP 200.

Placement rules: docs/landing may be public at `<project>.phenotype.space`; apps and backends never go on that host (see docs/governance/web-surface-rules.md).
