# Audit justification: pheno-cdylib-bridge → pheno (crates/pheno-cdylib-bridge)

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry row `repo-pheno-cdylib-bridge`
**Decision**: ABSORB → pheno monorepo `crates/pheno-cdylib-bridge/` (squash merge)

## Why absorb?

1. **Squash merge completed**: PR `pheno#282` (commit `c3f47016`, 2026-07-17)
   imported the substrate family of 4 crates (pheno-cdylib-bridge,
   pheno-runtime-config, pheno-context, pheno-forge-smoke) in a single squash.

2. **Single-language, single-crate**: pure Rust `cdylib` exposing
   `MemoryPort` FFI to Go/Python/C. 72 KB, self-contained, no frontend.

3. **Canonical home verified on remote**: `pheno/crates/pheno-cdylib-bridge/`
   exists on `main` HEAD with Cargo.toml + src/lib.rs + tests/.

4. **Source repo confirmed empty/redirected**: post-merge the upstream GH repo
   has no further activity (pushed 2026-08-02 then archived).

## Why not merge elsewhere

We deliberately did NOT target:
- `KooshaPari/phenotype-go-sdk` — Go SDK is a consumer, not the FFI host.
- `KooshaPari/phenotype-python-sdk` — same.
- `KooshaPari/pheno/runtime-config` — config layer, not the FFI layer.

## State captured

| Aspect | State at absorption |
| --- | --- |
| size_kb | 72 |
| open_issues | 0 |
| stars/forks | 0 / 0 |
| last_push | 2026-08-02 |
| archived_at | 2026-08-02 |

## Absorb technique

- Squash (PR #282) — full file content present, source SHA preserved in merge
  commit body but not in tree
- Verified on remote HEAD via
  `gh api repos/KooshaPari/pheno/contents/crates/pheno-cdylib-bridge`

## Forward-looking note

This row supersedes the prior `B:WORKING` classification (frozen 2026-07-18).
DELETE-SAFE as of 2026-09-01; `gh repo delete` may be issued once user
confirmation is received.

## References

- PR `pheno#282` (commit `c3f47016`)
- target row: `repo-pheno-cdylib-bridge` (registry v1.6.83)
- boundary: `docs/boundary/pheno-cdylib-bridge.md`
- sibling absorbs: pheno-runtime-config, pheno-context, pheno-forge-smoke
  (all in PR #282)
