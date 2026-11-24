# Wave 11 P3 phenoShared wave 4 — HexaKit

**Date:** 2026-06-17  
**Predecessor:** P3 wave 3 ([#258](https://github.com/KooshaPari/HexaKit/pull/258))

## Workspace exclude + git pin

| Crate | Canonical |
|-------|-----------|
| `phenotype-security-aggregator` | phenoShared |
| `phenotype-async-traits` | phenoShared |
| `phenotype-macros` | phenoShared |

## Deferred

| Crate | Blocker |
|-------|---------|
| `phenotype-contracts` | API diverge — HexaKit exports `InMemory*` adapters; phenoShared HEAD is `Contract`/`Event`/`MetricsHook` traits |

`phenotype-core` resolves `phenotype-async-traits` via workspace git dep; `phenotype-contracts` stays path-local until re-export alignment.
