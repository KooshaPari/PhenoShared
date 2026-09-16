# Audit justification: pheno-runtime-config → pheno (crates/pheno-runtime-config)

**Date**: 2026-07-17
**Author**: Forge (registry absorption wave 2026-07-17)
**Reference**: registry row `repo-pheno-runtime-config`
**Decision**: ABSORB → pheno monorepo `crates/pheno-runtime-config/`

## Why absorb?

1. **Single-language, single-crate**: pure Rust library, no frontend, no
   external service surface, 405 LOC + ~6 KB tests. The crate is
   bounded — it does not depend on any other Phenotype repo.

2. **No active downstream dependents outside pheno**: per ADR-095 the
   consumers are all `pheno-*` or `agileplus-*` binaries that will end
   up in either pheno or AgilePlus monorepo.

3. **Maintenance fragmentation**: the previous 2026-06-28 push at the
   standalone repo was a contract — the source-of-truth now lives at
   pheno (post-Airlock reorganization), and any pheno-runtime-config
   code change should land in the workspace, not in the orphan repo.

4. **Single-AUTH git history**: keeping a single shippable Rust
   workspace reduces dependency-failure modes (notably the 2026-07-04
   outage traced to the standalone repo not picking up `notify` v6.1.4
   in lockstep with pheno).

## Why not merge elsewhere

We deliberately did NOT target:
- `KooshaPari/Configra` — Configra is for static config (TOML/JSON),
  not hot-reloadable runtime state.
- `KooshaPari/PhenoObservability` — observability is a consumer, not
  a config loader.
- `KooshaPari/Authvault` — Authvault is for secrets/credentials, not
  generic runtime config.

## State captured

| Aspect   | State at absorption |
| -------- | -------------------- |
| size_kb  | 10                   |
| branches | 1 (main)             |
| last_push | 2026-06-28           |

## Forward-looking note

The `gw-pheno` gate (registry row, fsm=in-progress) plans to dismantle
the pheno monorepo around 2026-08-01, redistributing agileplus-* crates
to `KooshaPari/AgilePlus` and the remaining phenotype-* crates to their
respective owners. At that time, pheno-runtime-config will move from
`pheno/crates/pheno-runtime-config` to
`AgilePlus/crates/pheno-runtime-config`. This registry row will be
re-affirmed accordingly.

## References

- ADR-095 (Reloadable<T> pattern)
- src/lib.rs at `prc-scratch/src/lib.rs` (cloned for content audit)
- target row: `repo-pheno-runtime-config` (registry v1.6.30)
- absorption record: `docs/absorption/pheno-runtime-config/README.md`
- boundary: `docs/boundary/pheno-runtime-config.md`
