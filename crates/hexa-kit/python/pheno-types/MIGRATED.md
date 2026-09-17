# Migration: pheno-types → phenotype-types

**Date:** 2026-06-16  
**Disposition step:** HexaKit DISPOSITION #4 — `python/pheno-types` stub redirect  
**Canonical repo:** https://github.com/KooshaPari/phenotype-types

## What changed

- Implementation, tests, and package source were removed from `HexaKit/python/pheno-types`.
- This path is now a **pointer stub** only (README + metadata).
- Runtime types are owned by **`phenotype-types`**, not HexaKit.

## For consumers

1. Depend on `pheno-types` from the canonical Git repository (see [README.md](./README.md)).
2. Import path is unchanged: `from pheno_types import ...`
3. Do not install `-e python/pheno-types` from HexaKit for new work.

## For HexaKit maintainers

- Other `python/pheno-*` packages are relocated in separate lanes — do not modify them here.
- Remove this stub directory once downstream references are cleared (follow-up PR).
