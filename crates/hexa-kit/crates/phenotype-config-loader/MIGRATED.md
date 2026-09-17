# Migration: phenotype-config-loader → phenotype-config

**Date:** 2026-06-17  
**Wave 14 (ADR-ECO-014):** Terminal owner repoint from interim phenoShared staging  
**Disposition step:** HexaKit DISPOSITION #8 — Wave E absorption stub  
**Canonical repo:** https://github.com/KooshaPari/phenotype-config  
**ADR:** [ADR-ECO-014-phenoshared-decompose](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/adrs/ADR-ECO-014-phenoshared-decompose.md)

## What changed

- Implementation ownership moves to **phenotype-config** (`config` role per DOMAIN_ROLES).
- phenoShared was **interim staging only** — not a terminal repoint target.
- Loader concepts may consolidate into `settly`; see `crates/settly/CANONICAL_FROM_PHENO_SHARED_CONFIG.md` in phenotype-config.
- This HexaKit path is a **pointer stub** until downstream references are cleared.

## For consumers

1. Depend on `phenotype-config-loader` from **phenotype-config**, not phenoShared or HexaKit:

```toml
phenotype-config-loader = { git = "https://github.com/KooshaPari/phenotype-config", branch = "main" }
```

2. See DOMAIN_ROLES and disposition-index row id **8**.

## For HexaKit maintainers

- Do not add new phenoShared pins for this crate.
- Remove this stub directory once workspace members and downstream refs are repointed.
