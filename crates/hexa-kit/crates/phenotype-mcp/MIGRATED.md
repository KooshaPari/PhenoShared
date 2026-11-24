# Migration: phenotype-mcp → substrate

**Date:** 2026-06-17  
**Disposition step:** HexaKit DISPOSITION #28 — Wave D absorption stub  
**Canonical repo:** https://github.com/KooshaPari/substrate

## What changed

- Implementation ownership moves to **substrate** (`crates/phenotype-mcp`).
- McpKit retired per registry #100; MCP primitives live in substrate.
- **Source tree removed** from HexaKit; only this redirect stub remains.

## For consumers

1. Depend on `phenotype-mcp` from substrate, not HexaKit:

```toml
phenotype-mcp = { git = "https://github.com/KooshaPari/substrate", branch = "main" }
```

2. See DOMAIN_ROLES and disposition-index row id **28**.

## For HexaKit maintainers

- Do not extend domain logic under `crates/phenotype-mcp`.
- Remove this stub directory once zero external path deps remain.
