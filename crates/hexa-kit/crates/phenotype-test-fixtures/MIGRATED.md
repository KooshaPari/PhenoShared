# Migration: phenotype-test-fixtures → TestingKit

**Date:** 2026-06-18  
**Disposition row:** HexaKit DISPOSITION #41 — Wave B  
**Canonical repo:** https://github.com/KooshaPari/TestingKit  
**Git pin:** `TestingKit` branch `main`

## What changed

- Local source **pruned** Phase 3 — this directory is a redirect stub only.
- Canonical implementation at `TestingKit/rust/phenotype-test-fixtures`.

## For consumers

```toml
phenotype-test-fixtures = { git = "https://github.com/KooshaPari/TestingKit", branch = "main", package = "phenotype-test-fixtures" }
```
