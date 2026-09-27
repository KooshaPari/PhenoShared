# STATUS.md — phenotype-landing

## Work State

**ACTIVE** · **Progress:** `██████░░░░ 80%`

## Current Phase

Phase 1 — Tooling standardization + template system foundation.

## Completed

- [x] All 7 landing sites merged into monorepo via `git subtree`
- [x] Standalone landing repos deleted (`agileplus-landing`, `byteport-landing`, `hwledger-landing`, `phenokits-landing`, `thegent-landing`)
- [x] `x-landings` duplicate repo removed (never should have existed)
- [x] CI matrix build for all 6 Astro sites (odin-landing is static HTML)
- [x] Pinned CI actions to commit SHAs
- [x] AGENTS.md added

## In Progress

- [ ] Taskfile.yml with SSOT recipes
- [ ] packages/ directory with shared components (ui, github-fetcher, design-tokens)
- [ ] templates/ directory with generic landing page template
- [ ] Generator script to read project config from `.phenotype/` or `docs/`
- [ ] projects-landing robustness improvements (API-based, not gh CLI)

## Next Steps

1. Add Taskfile.yml for quality gates
2. Extract shared components into packages/
3. Design generic landing template
4. Add config-driven generation from project repos
5. Modernize projects-landing fetch script

## Notes

- `phenotype-landing` is the canonical monorepo for all org landing pages.
- `projects-landing` inside `sites/` is the `projects.kooshapari.com` portfolio.
- `odin-landing` is static HTML (no build); excluded from Astro CI matrix.
- Each site is an independent Astro package with its own `package.json` and lockfile.
