# Wave 10 P3 phenoShared wave 3 — HexaKit

**Date:** 2026-06-17  
**Predecessor:** P3 wave 2 ([#256](https://github.com/KooshaPari/HexaKit/pull/256))

## Workspace exclude + git pin

| Crate | Canonical |
|-------|-----------|
| `phenotype-logging` | phenoShared |
| `phenotype-time` | phenoShared |
| `phenotype-state-machine` | phenoShared |
| `phenotype-policy-engine` | phenoShared |

`phenotype-core` umbrella resolves state-machine, policy-engine, and time via workspace git deps.
