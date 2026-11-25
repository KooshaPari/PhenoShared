# Migration: phenotype-http-client-core → phenoShared

**Date:** 2026-06-17  
**Disposition step:** HexaKit DISPOSITION #23 — Wave D reroute (ResilienceKit KEEP_ARCHIVED)  
**Canonical repo:** https://github.com/KooshaPari/phenoShared

## What changed

- Registry target rerouted from **ResilienceKit** (KEEP_ARCHIVED) to **phenoShared** per stashly pattern.
- Canonical implementation at `phenoShared/crates/phenotype-http-client-core`.
- **Source tree removed** from HexaKit; only this redirect stub remains.

## For consumers

1. Depend on `phenotype-http-client-core` from phenoShared, not HexaKit or ResilienceKit:

```toml
phenotype-http-client-core = { git = "https://github.com/KooshaPari/phenoShared", branch = "main" }
```

2. See DOMAIN_ROLES and disposition-index row id **23**.

## For HexaKit maintainers

- Do not unarchive ResilienceKit for this crate.
- Remove this stub directory once fleet repoint completes.
