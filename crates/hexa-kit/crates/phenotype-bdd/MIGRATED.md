# Migration: phenotype-bdd → TestingKit

**Date:** 2026-06-17  
**Disposition step:** HexaKit DISPOSITION #4 — Wave B testing lane stub  
**Canonical repo:** https://github.com/KooshaPari/TestingKit

## What changed

- Implementation ownership moves to **TestingKit** (`rust/phenotype-bdd` when landed).
- This HexaKit path is a **pointer stub** until downstream references are cleared.
- Do not extend BDD harness logic here; contribute to TestingKit instead.

## For consumers

1. Depend on `phenotype-bdd` from TestingKit (path or git pin), not HexaKit.
2. Crate name remains `phenotype-bdd`.
3. See [TestingKit wave-b absorption doc](https://github.com/KooshaPari/TestingKit/blob/main/docs/disposition/wave-b-absorption.md).

## For HexaKit maintainers

- Remove this crate directory once workspace members and downstream refs are repointed (follow-up PR).
- Registry row: `disposition-index.json` id **4**, wave **B**, target **TestingKit**.
