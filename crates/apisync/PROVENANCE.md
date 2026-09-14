# PROVENANCE

## Source Repository
- **Name**: Apisync
- **URL**: https://github.com/KooshaPari/Apisync
- **Version at absorption**: 0.2.10
- **License**: MIT OR Apache-2.0

## Absorption Details
- **Absorbed by**: KooshaPari/pheno
- **Date**: 2026-09-14
- **Commit at source**: (depth=1 clone, see git log)
- **Target path**: crates/apisync/

## Files Absorbed
Full source tree from Apisync, including:
- `src/` — Rust source code (adapters, application, clients, domain, infrastructure)
- `tests/` — Integration and property tests
- `benches/` — Criterion benchmarks
- `docs/` — Documentation (architecture, ADRs, API, quickstart, VitePress config)
- `fuzz/` — cargo-fuzz targets
- `scripts/` — CI helper scripts
- `assets/` — Brand assets (SVGs)
- Configuration files (Cargo.toml, Cargo.lock, rustfmt.toml, deny.toml, etc.)
- GitHub workflows and templates

## Notes
- This crate is absorbed as-is; no modifications to existing pheno crates were made.
- The workspace Cargo.toml was updated to include this crate as a member.
- The crate retains its original dependency set; workspace deduplication may be applied later.
