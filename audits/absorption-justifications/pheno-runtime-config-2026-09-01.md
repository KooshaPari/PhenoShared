# Audit justification: pheno-runtime-config → pheno (crates/pheno-runtime-config)

**Date**: 2026-09-01
**Author**: Forge (13-source polyrepo audit, wave J)
**Reference**: registry row `repo-pheno-runtime-config`
**Decision**: ABSORB → pheno monorepo `crates/pheno-runtime-config/` (squash merge)

## Why absorb?

1. **Squash merge completed**: PR `pheno#282` (commit `c3f47016`, 2026-07-17)
   imported the substrate family of 4 crates including pheno-runtime-config.

2. **Single-language, single-crate**: pure Rust library implementing the
   `Reloadable<T>` trait pattern (ADR-095), `notify` watcher, SIGHUP fallback,
   `arc-swap` atomic. 28 KB.

3. **Canonical home verified on remote**: `pheno/crates/pheno-runtime-config/`
   exists on `main` HEAD with Cargo.toml + src/lib.rs + tests/.

4. **Legacy classification flipped**: prior registry row said
   `ARCHIVE_ONLY → B:WORKING (live flip)` during the 2026-07-17 absorption
   wave. After absorption + 6 fix-up patches during squash, the disposition
   is correctly `ABSORB`.

## Why not merge elsewhere

We deliberately did NOT target:
- `KooshaPari/Configra` — Configra is for static config (TOML/JSON), not
  hot-reloadable runtime state.
- `KooshaPari/PhenoObservability` — observability is a consumer.
- `KooshaPari/Authvault` — secrets/credentials layer.

## State captured

| Aspect | State at absorption |
| --- | --- |
| size_kb | 28 |
| open_issues | 0 |
| stars/forks | 0 / 0 |
| last_push | 2026-08-05 |
| archived_at | 2026-08-05 |
| visibility | private |

## Absorb technique

- Squash (PR #282) — 1/4 of the substrate family
- Verified on remote HEAD via
  `gh api repos/KooshaPari/pheno/contents/crates/pheno-runtime-config`

## Forward-looking note

This row supersedes the prior `B:WORKING` classification (frozen 2026-07-18).
DELETE-SAFE as of 2026-09-01; `gh repo delete` may be issued once user
confirmation is received. Note: the source repo was **private** (visibility
flipped during the absorption wave). The deletion will be issued under the
operator's personal GitHub namespace.

## References

- PR `pheno#282` (commit `c3f47016`)
- prior justification: `pheno-runtime-config-2026-07-17.md`
- target row: `repo-pheno-runtime-config` (registry v1.6.83)
- boundary: `docs/boundary/pheno-runtime-config.md`
- ADR-095 (Reloadable<T> pattern)
