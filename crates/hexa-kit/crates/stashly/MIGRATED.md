# Migration: stashly → phenoShared / phenotype-types

**Date:** 2026-06-17  
**Disposition row:** HexaKit DISPOSITION #46 — `crates/stashly`  
**Canonical repos:** https://github.com/KooshaPari/phenoShared (Rust cache infra) · https://github.com/KooshaPari/phenotype-types (shared types)  
**Charter:** v2 boundary-shaping — cache role → phenoShared / phenotype-types

## What changed

- Removed `crates/stashly` from the HexaKit workspace members (P2 excision).
- Canonical cache implementation lives in **phenoShared**; shared type bindings in **phenotype-types**.
- **Source tree removed** from HexaKit; only this redirect stub remains until fleet repoint completes.

## For consumers

1. Depend on `stashly` from **phenoShared**, not HexaKit `crates/stashly`.
2. Git dependency (fleet default):

```toml
stashly = { git = "https://github.com/KooshaPari/phenoShared", branch = "main" }
```

3. TypeScript/Python shared types → **phenotype-types** — see [phenotype-types](https://github.com/KooshaPari/phenotype-types).

## For HexaKit maintainers

- Do not add new cache-domain code under `crates/stashly`.
- Remove this stub directory once zero external path deps remain.
