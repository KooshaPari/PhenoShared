# Migration: pheno-mcp → PhenoMCP + substrate

**Date:** 2026-06-18  
**Disposition step:** Wave F — `python/pheno-mcp` stub redirect  
**Canonical repos:**
- Python library: https://github.com/KooshaPari/PhenoMCP
- Rust MCP runtime: https://github.com/KooshaPari/substrate (`crates/phenotype-mcp`)

## What changed

- Implementation, tests, and package source were removed from `HexaKit/python/pheno-mcp`.
- This path is now a **pointer stub** only (README + metadata).
- Registry row `py-pheno-mcp` target is **substrate** (runtime); Py install surface is PhenoMCP.

## For consumers

1. Install Python MCP tooling from PhenoMCP, not HexaKit `python/pheno-mcp`.
2. Rust MCP runtime → substrate `phenotype-mcp` (substrate#28).
3. Do not install `-e python/pheno-mcp` from HexaKit for new work.

## For HexaKit maintainers

- Remove this stub directory once downstream references are cleared (follow-up PR).
