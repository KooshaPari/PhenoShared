# Error overlap canonical-boundary audit

## Decision

Treat `pheno/crates/phenotype-error-core` plus its `phenotype-errors` facade as the current concrete canonical parent candidate. This is a boundary decision, not a claim that all same-named implementations are equivalent.

## Evidence

- `KooshaPari/pheno-errors` is private scratch residue at `01b850e4`; it has no Cargo manifest or Rust source.
- `pheno` contains the implemented layered error core and facade.
- OmniRoute and PlayCua contain parent-local/app-local implementations with different coupling and semantics.
- PhenoObservability and Agentora contain transitional/vendor or deprecated facades.
- The documented upstream `phenoShared` and `phenotype-types` targets currently return 404.

## Required before archival

1. Preserve immutable remote and local history for each duplicate surface.
2. Add compatibility/migration tests for any code proposed for consolidation.
3. Resolve the missing upstream provenance or explicitly supersede it.
4. Obtain sponsor approval before archiving any remote repository.

No remote was archived, deleted, or rewritten by this audit.
