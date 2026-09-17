# Canonical Source Notice

**This crate has been promoted to the `phenoShared` workspace.**

The canonical source for `phenotype-health` now lives at:

- Repository: https://github.com/KooshaPari/phenoShared
- Path: https://github.com/KooshaPari/phenoShared/tree/main/crates/phenotype-health

## Status

The copy in this repository (`pheno/crates/phenotype-health/`) is **deprecated** and retained only for backward compatibility with existing path-based consumers. No new feature work should land here.

## Migration Guidance

New consumers should depend on the `phenoShared` version. Existing consumers will be migrated forward-only as part of the Phase 2 reuse rollout (see `phenoShared` PR #102 and follow-up tracking).

Do **not** edit this copy for non-trivial changes — open the change against `phenoShared` instead, then re-sync.
