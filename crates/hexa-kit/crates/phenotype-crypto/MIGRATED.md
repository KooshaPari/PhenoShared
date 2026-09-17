# Migration: phenotype-crypto → Authvault

**Disposition id:** 15  
**Target:** `<REDACTED>/Authvault` → `rust/phenotype-crypto`  
**Wave:** C

Canonical implementation lives in Authvault. Depend via git pin:

```toml
phenotype-crypto = { git = "https://github.com/KooshaPari/Authvault", branch = "main", package = "phenotype-crypto" }
```
