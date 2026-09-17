# Migration: phenotype-contracts → phenoShared

**Date:** 2026-06-17  
**Wave 13 lane C** — traits canonical in phenoShared; HexaKit scaffold retains `phenotype-contract-adapters` for `InMemory*` test adapters.

## Canonical

- Traits: https://github.com/KooshaPari/phenoShared/tree/main/crates/phenotype-contracts
- Adapters (scaffold): `crates/phenotype-contract-adapters` in HexaKit workspace

## Consumers

Use `phenotype-contracts` from phenoShared for canonical traits. Use `phenotype-contract-adapters` or `phenotype_core::contracts` for in-memory adapters.
