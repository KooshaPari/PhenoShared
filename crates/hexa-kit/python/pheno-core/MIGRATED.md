# Migration: pheno-core → phenotype-python-sdk

**Date:** 2026-06-18  
**Disposition step:** Wave F — `python/pheno-core` stub redirect  
**Canonical repo:** https://github.com/KooshaPari/phenotype-python-sdk

## What changed

- Implementation, tests, and package source were removed from `HexaKit/python/pheno-core`.
- This path is now a **pointer stub** only (README + metadata).
- Shared Python base is owned by **phenotype-python-sdk**, not phenoShared (ADR-ECO-014).

## For consumers

1. Depend on `phenotype-python-sdk` from the canonical Git repository (see [README.md](./README.md)).
2. Do not install `-e python/pheno-core` from HexaKit for new work.

## For HexaKit maintainers

- Remove this stub directory once downstream references are cleared (follow-up PR).
