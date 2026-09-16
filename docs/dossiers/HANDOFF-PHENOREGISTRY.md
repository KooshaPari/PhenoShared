# PhenoRegistry Absorption Handoff

**Date:** 2026-09-16 (Pacific)
**Source:** KooshaPari/PhenoRegistry (absorbed commit `f7ab4cdb`)
**Agent:** horse session (`session_horse_1789548992881`)

## What Was Done

PhenoRegistry content absorbed into PhenoShared:
- 3,848 files added, ~2.1M lines absorbed
- Content landed in `registry/`, `crates/`, `archives/`, `docs/`

### Absorbed Content Locations

| Location | Contents |
|----------|----------|
| `registry/` | Master index: disposition-index.json, components.lock, domain-roles.json, chokepoints.json, audit JSONs, absorbed-crates/, specs/ |
| `crates/pheno-registry-python/` | PyO3 Python SDK for phenotype-registry (NOT in workspace) |
| `crates/phenotype-project-registry/` | Project registry crate (NOT in workspace) |
| `crates/phenotype-service-registry/` | Service discovery crate, hexagonal port + in-memory adapter (NOT in workspace) |
| `archives/zz-archive-phenotype-registry/` | Recovery/deletion archive: 234 files from origin deletion |

## What Remains (NOT DONE)

### 1. ~~Workspace Member Registration~~ DONE

Two PhenoRegistry crates added to workspace members, one left orphaned:

| Crate | Status | Notes |
|-------|--------|-------|
| `phenotype-project-registry` | **INTEGRATED** | Added missing deps (anyhow, phenotype-health, tokio), switched phenotype-health to local path |
| `phenotype-service-registry` | **INTEGRATED** | Already clean, uses workspace deps |
| `pheno-registry-python` | ORPHANED | Depends on non-existent `phenotype-registry` crate. Stays out of workspace |

### 2. Registry Data Audit

The `registry/` directory contains operational data that needs classification:
- `disposition-index.json` (663KB) - master disposition decisions
- `components.lock` - component lockfile
- `domain-roles.json` - domain role assignments
- `chokepoints.json` - chokepoint analysis
- `absorbed-crates/` - data from 7 absorbed packages (apisync, DataKit, eidolon, pheno-forge-smoke, Planify, stashly, thegent)
- `audit-*.json` - audit artifacts
- `specs/` - specification data

### 3. Registry Integration Questions

- Should `phenotype-project-registry` and `phenotype-service-registry` be added to workspace?
- What consumers depend on these crates externally?
- Should the `registry/` data dir be gitignored or tracked?
- `pheno-registry-python` needs rewrite or removal (broken dep chain)

## Dependencies on Other Absorptions

- `phenotype-service-registry` references `phenotype-tooling` repo (origin URL still in Cargo.toml)
- `pheno-registry-python` references non-existent `phenotype-registry` crate

## Blocking Issues

None for `cargo check --workspace` (these crates are not in workspace). The 3 crates are orphaned but harmless.

## Next Steps

1. Decide whether `phenotype-project-registry` and `phenotype-service-registry` join workspace
2. Fix or remove `pheno-registry-python` (broken path dep)
3. Classify `registry/` data directory for tracking/gitignore
4. Update origin URLs in absorbed crate Cargo.toml files
