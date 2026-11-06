# AGENTS.md — phenotype-landing

## Status

**ACTIVE** — Monorepo of Phenotype org landing pages. All sites are merged and stable.

## Repository

- **Owner**: Phenotype org / KooshaPari
- **Stack**: Astro 6, Bun, TypeScript, Tailwind (per sub-package)
- **CI**: GitHub Actions matrix build for all `sites/*`
- **License**: MIT

## Governance

- `CLAUDE.md` — Claude Code project instructions
- `README.md` — Monorepo layout and per-site dev instructions
- `STATUS.md` — Work state and progress tracker
- `.github/workflows/ci.yml` — Matrix build for all landing sites
- `packages/` — Shared components and templates
- `templates/` — Generic landing page templates

## Agent Rules

- Do not modify unrelated landings in the same PR.
- Prefer shared `packages/` components over per-site duplication.
- Run `bunx astro check` and `bun run build` before committing.
- Follow the `Taskfile.yml` SSOT recipes for quality gates.

## Quick Start

```bash
# Build all sites
task build

# Build a specific site
task build -- sites/byteport-landing

# Quality gate for all sites
task quality
```

## Worklogs

- `docs/worklogs/` — Hub-specific work audit index (if applicable)
