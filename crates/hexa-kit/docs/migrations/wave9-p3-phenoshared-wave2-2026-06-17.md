# Wave 9 P3 phenoShared wave 2 — HexaKit

**Date:** 2026-06-17  
**Predecessor:** P3 wave 1 ([#252](https://github.com/KooshaPari/HexaKit/pull/252) — error crates)

## Workspace exclude + git pin

| Crate | Canonical |
|-------|-----------|
| `phenotype-event-bus` | phenoShared |
| `phenotype-event-sourcing` | phenoShared |
| `phenotype-http-client-core` | phenoShared |

Local stub trees (`MIGRATED.md`) retained; members removed; `workspace.dependencies` git-pin to phenoShared `main`.

## Consumer note

`phenotype-core` remains a transitional HexaKit member and resolves these via workspace git deps.
