# Wave eco-consolidate — HexaKit stub prune batch (2026-06-17)

**PR:** HexaKit #255 (feat/eco-consolidate-wave-e-d)  
**Prereq merges:** phenoShared #177, substrate #28, TestingKit #7  
**Builds on:** P3 waves 1–4 (#256, #258, #260)

## Crates excluded + stub-pruned (this PR)

| Crate | Disposition id | Canonical target |
|-------|----------------|------------------|
| phenotype-config-loader | 8 | phenoShared |
| phenotype-mcp | 28 | substrate |
| phenotype-test-infra | 40 | TestingKit |
| phenotype-event-bus | 19 | phenoShared (stub prune; excluded in #256) |
| phenotype-http-client-core | 23 | phenoShared (MIGRATED reroute) |

## Workspace changes

- Removed workspace members for config-loader, mcp, test-infra.
- Added `exclude` entries (eco-consolidate tail).
- Git pins: config-loader → phenoShared, mcp → substrate.

## Verification

```bash
cargo check -p phenotype-core
```
