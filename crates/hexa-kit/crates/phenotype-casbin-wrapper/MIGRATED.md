# Migration: phenotype-casbin-wrapper → Authvault

**Date:** 2026-06-17  
**Disposition id:** 6 (ADR-ECO-015)  
**Canonical repo:** https://github.com/KooshaPari/Authvault → `rust/phenotype-casbin-wrapper`

## For consumers

```toml
phenotype-casbin-wrapper = { git = "https://github.com/KooshaPari/Authvault", branch = "main", package = "phenotype-casbin-wrapper" }
```

policy-engine `casbin-backend` feature should pin Authvault, not HexaKit.
