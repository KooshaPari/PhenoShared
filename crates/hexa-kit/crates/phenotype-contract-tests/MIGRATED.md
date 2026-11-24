# Migration: phenotype-contract-tests → TestingKit

**Date:** 2026-06-17  
**Disposition step:** HexaKit DISPOSITION #12 — Wave B testing lane stub  
**Canonical repo:** https://github.com/KooshaPari/TestingKit

## What changed

- Contract test runner ownership moves to **TestingKit** (`rust/phenotype-contract-tests` when landed).
- This HexaKit path did not have a standalone crate checkout at stub time; this file marks the disposition row.
- Relocate together with `phenotype-contract` and `phenotype-contracts`.

## For consumers

1. Depend on `phenotype-contract-tests` from TestingKit when the crate lands there.
2. See [TestingKit wave-b absorption doc](https://github.com/KooshaPari/TestingKit/blob/main/docs/disposition/wave-b-absorption.md).

## For HexaKit maintainers

- No implementation to delete here yet; ensure any in-tree contract-test runners repoint to TestingKit.
- Registry row: `disposition-index.json` id **12**, wave **B**, target **TestingKit**.
