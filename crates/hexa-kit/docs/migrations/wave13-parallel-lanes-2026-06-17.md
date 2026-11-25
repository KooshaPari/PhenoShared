# Wave 13 — parallel lanes — HexaKit

**Date:** 2026-06-17  
**Predecessor:** [wave12-health-cache-phenoshared-2026-06-17.md](./wave12-health-cache-phenoshared-2026-06-17.md)

## Lane A — config-loader (pre-merged eco-consolidate)

Already on `main`: `phenotype-config-loader` excluded + git pin → phenoShared (#255).

## Lane B — test infra → TestingKit

- Exclude `phenotype-test-infra`; workspace git pin → TestingKit
- Disposition rows #4, #40 updated

## Lane C — contracts split

| Component | Location |
|-----------|----------|
| Canonical traits | phenoShared `phenotype-contracts` (git pin) |
| `InMemory*` adapters | HexaKit `phenotype-contract-adapters` (scaffold member) |

`phenotype-core::contracts` re-exports adapters from scaffold crate.

## Lane D — cipher → Authvault

- Exclude `crates/cipher`; git pin → `Authvault/rust/phenotype-cipher`
- Authvault workspace absorption pre-landed on `main`

## Verification

```bash
cargo check -p phenotype-core -p phenotype-contract-adapters -p hexakit-cli
```
