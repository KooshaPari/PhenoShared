# Migration: phenotype-contract → TestingKit

**Date:** 2026-06-18  
**Disposition row:** HexaKit DISPOSITION #10 — Wave B  
**Canonical repo:** https://github.com/KooshaPari/TestingKit  
**Git pin:** `TestingKit` branch `main` (TestingKit#9)

## What changed

- Local source **pruned** Phase 3 — this directory is a redirect stub only.
- Canonical implementation at `TestingKit/rust/phenotype-contract`.

## For consumers

```toml
phenotype-contract = { git = "https://github.com/KooshaPari/TestingKit", branch = "main", package = "phenotype-contract" }
```
