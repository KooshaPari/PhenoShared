# Audit justification: pheno-forge-smoke → pheno (crates/pheno-forge-smoke)

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry row `repo-pheno-forge-smoke-audit20260901`
**Decision**: ABSORB → pheno monorepo `crates/pheno-forge-smoke/` (squash merge)

## Why absorb?

1. **Squash merge completed**: PR `pheno#282` (commit `c3f47016`, 2026-07-17)
   imported pheno-forge-smoke as part of the substrate family (4th of 4).

2. **Single-language, single-binary**: pure Rust binary that loads
   `libpheno_bridge` via `libloading` and exercises composite routing per
   ADR-096. 90 KB, with `sidecars/` directory for forgecode sidecar harness.

3. **Canonical home verified on remote**: `pheno/crates/pheno-forge-smoke/`
   exists on `main` HEAD with Cargo.toml + src/main.rs + sidecars/.

4. **No prior registry row**: this source was missing from
   `phenotype-registry/registry/disposition-index.json` as of 2026-07-18
   freeze. New row `repo-pheno-forge-smoke-audit20260901` added 2026-09-01
   to close the gap.

## Why not merge elsewhere

We deliberately did NOT target:
- `KooshaPari/phenotype-tooling` — tooling layer, not the substrate layer.
- `KooshaPari/pheno-forge-plugins` — different scope (6 sidecar plugins,
  not the smoke binary).

## State captured

| Aspect | State at absorption |
| --- | --- |
| size_kb | 90 |
| open_issues | 0 |
| stars/forks | 0 / 0 |
| last_push | 2026-08-02 |
| archived_at | 2026-08-02 |

## Absorb technique

- Squash (PR #282) — 4/4 of the substrate family
- Verified on remote HEAD via
  `gh api repos/KooshaPari/pheno/contents/crates/pheno-forge-smoke`

## Forward-looking note

This row was missing from the 2026-07-18 registry freeze; added 2026-09-01.
DELETE-SAFE as of 2026-09-01; `gh repo delete` may be issued once user
confirmation is received.

## References

- PR `pheno#282` (commit `c3f47016`)
- prior justification: `pheno-forge-smoke-2026-07-17.md`
- target row: `repo-pheno-forge-smoke-audit20260901` (registry v1.6.83, NEW)
- boundary: `docs/boundary/pheno-forge-smoke.md`
- ADR-096 (composite routing via libloading)
