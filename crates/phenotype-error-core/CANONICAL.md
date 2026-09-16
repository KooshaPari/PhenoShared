# Canonical Source Notice

**This crate has been promoted to the `phenoShared` workspace.**

The canonical source for `phenotype-error-core` now lives at:

- Repository: https://github.com/<REDACTED>/phenoShared
- Path: https://github.com/<REDACTED>/phenoShared/tree/main/crates/phenotype-error-core

## Status

The copy in this repository (`pheno/crates/phenotype-error-core/`) is **deprecated** and retained only for backward compatibility with existing path-based consumers. No new feature work should land here.

## Supersession Notice

The standalone `pheno-errors` crate (`<REDACTED>/pheno-errors`) — which defined a 5-variant `AppError` enum (`Domain`, `NotFound`, `Conflict`, `Validation`, `Storage`) with convenience constructors, `kind()` tags, and `log_warn`/`log_error` helpers — is **superseded** by this crate. All semantic error patterns from `pheno-errors` map directly to variants in `phenotype-error-core`:

| `pheno-errors` variant | `phenotype-error-core` equivalent |
|---|---|
| `AppError::Domain` | `DomainError` (multiple variants) |
| `AppError::NotFound { entity, id }` | `DomainError::NotFound { entity, id }` |
| `AppError::Conflict` | `DomainError::Duplicate` / `ApiError::Conflict` |
| `AppError::Validation` | `DomainError::Validation` |
| `AppError::Storage` | `StorageError` (multiple variants) |

The utility methods (`kind()`, `log_warn()`, `log_error()`, `From<anyhow::Error>`) from `pheno-errors` are not carried forward into this crate; consumers should use the richer layered error types directly.

## Migration Guidance

New consumers should depend on the `phenoShared` version. Existing consumers will be migrated forward-only as part of the Phase 2 reuse rollout (see `phenoShared` PR #102 and follow-up tracking).

Do **not** edit this copy for non-trivial changes — open the change against `phenoShared` instead, then re-sync.
