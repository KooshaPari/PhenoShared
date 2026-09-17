# Migration: phenotype-macros → phenoShared

**Date:** 2026-06-17  
**Disposition step:** HexaKit DISPOSITION #18 — Wave E absorption stub  
**Canonical repo:** https://github.com/KooshaPari/phenoShared

## What changed

- Implementation ownership moves to **phenoShared**.
- This HexaKit path is a **pointer stub** until downstream references are cleared.
- Do not extend domain logic here; contribute to phenoShared instead.

## For consumers

1. Depend on phenotype-macros from phenoShared (path or git pin), not HexaKit.
2. See DOMAIN_ROLES and disposition-index row id **18**.

## For HexaKit maintainers

- Remove this crate directory once workspace members and downstream refs are repointed.
