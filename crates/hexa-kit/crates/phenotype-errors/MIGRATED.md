# Migration: phenotype-errors → phenotype-types

**Date:** 2026-06-17  
**Wave 14 (ADR-ECO-014):** Terminal owner repoint from interim phenoShared staging  
**Disposition step:** HexaKit DISPOSITION #16 — Wave E absorption stub  
**Canonical repo:** https://github.com/KooshaPari/phenotype-types  
**ADR:** [ADR-ECO-014-phenoshared-decompose](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/adrs/ADR-ECO-014-phenoshared-decompose.md)

## What changed

- Implementation ownership moves to **phenotype-types** (`types` role per DOMAIN_ROLES).
- phenoShared was **interim staging only** — not a terminal repoint target.
- This HexaKit path is a **pointer stub** until downstream references are cleared.

## For consumers

1. Depend on `phenotype-errors` from **phenotype-types**, not phenoShared or HexaKit:

```toml
phenotype-errors = { git = "https://github.com/KooshaPari/phenotype-types", branch = "main" }
```

2. See DOMAIN_ROLES and disposition-index row id **16**.

## For HexaKit maintainers

- Do not add new phenoShared pins for this crate.
- Remove this stub directory once workspace members and downstream refs are repointed.
