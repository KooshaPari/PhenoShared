# Migration: cipher / phenotype-cipher → Authvault

**Date:** 2026-06-17  
**Disposition step:** HexaKit DISPOSITION #2 — Wave C absorption  
**Canonical repo:** https://github.com/KooshaPari/Authvault

## What changed

- Implementation ownership moves to **Authvault** at `rust/phenotype-cipher`.
- **Source tree removed** from HexaKit; only this redirect stub remains.

## For consumers

```toml
phenotype-cipher = { git = "https://github.com/KooshaPari/Authvault", branch = "main" }
```

## For HexaKit maintainers

- Do not extend domain logic under `crates/cipher`.
- Registry row: disposition-index id **2**, wave **C**, target **Authvault**.
