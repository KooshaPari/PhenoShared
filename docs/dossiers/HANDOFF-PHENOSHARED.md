# PhenoShared Comprehensive Handoff

**Date:** 2026-09-16 (Pacific)
**Branch:** main at `cd13e96a` (pending push of registry integration)
**Repo:** KooshaPari/PhenoShared (formerly PhenoAI)

## Repository Identity

- **Former name:** PhenoAI
- **Current name:** PhenoShared
- **Role:** Pooled foundation monorepo (Rust workspace + absorbed repos)
- **Workspace members:** 81 (79 + 2 newly integrated PhenoRegistry crates)
- **Total crate dirs:** 310
- **cargo check:** PASS (0 errors, 47 warnings)

## Absorption History (chronological)

| Commit | Repo Absorbed | Files | Lines | Key Content |
|--------|--------------|-------|-------|-------------|
| `8fdd395d` | PlayCua | - | - | Computer-use agent |
| `5f0ffd08` | Eidolon | - | - | Agent runtime |
| `eebd434b` | Gateway | - | - | Gateway routing + capacity |
| `365a3572` | PhenoFabric | 997 | 118K | fabric-* crates (21 crates) |
| `6c9b79ca` | PhenoInfra | - | - | Compute mesh IaC (OCI/CF/GCP/AWS/Vercel) |
| `a2437820` | PhenoLab | 1,553 | 510K | Compression stack, RLVR harness |
| `25c8dde1` | PhenoGfx | - | - | GFX SDK (Rust voxel + C# terrain/water) |
| `f7ab4cdb` | PhenoRegistry | 3,848 | 2.1M | Org registry, master index |
| `7a8ef302` | PhenoMLX | 587 | 81K | MLX inference engine, perf-core |

## Current Compilation Status

```
cargo check --workspace: PASS (0 errors)
Warnings: 47 (missing docs, unused imports, unused structs)
Future-compat: block v0.1.6, proc-macro-error2 v2.0.1
```

### Fixes Applied This Session (`0066e38b`)

1. Removed `optional = true` from workspace deps: `prometheus`, `wgpu`, `pollster`
2. Added `authors` to `[workspace.package]`
3. Fixed `phenotype-router`: dead git URL -> local path dep
4. Fixed `pheno-otel`: dead git URL -> local path dep, removed standalone `[workspace]`
5. Fixed `phenotype-voxel`: wrong path for `phenotype-gfx`, added `phenotype-gfx` to workspace
6. Aligned `rusqlite` versions: `fabric-persist` 0.31 -> workspace 0.40

## Orphaned Crates (absorbed but NOT in workspace members)

| Crate | Source Repo | Issue |
|-------|-------------|-------|
| `pheno-registry-python` | PhenoRegistry | Broken path dep to `phenotype-registry` (non-existent). Stays orphaned |

## Non-Rust Absorbed Content

| Location | Source | Status |
|----------|--------|--------|
| `registry/` | PhenoRegistry | Master index data (JSON, specs, audit artifacts) |
| `bench/` | PhenoLab | RLVR harness, evaluation tooling |
| `evals/` | PhenoMLX | MLX evaluation suites |
| `perf-core/` | PhenoMLX | Rust performance cores |
| `gui/` | PhenoMLX | MLX GUI |
| `sites/phenoregistry-landing/` | PhenoRegistry | Landing page |
| `apps/bench-cockpit/` | PhenoLab | Benchmark cockpit (Go + React) |
| `archives/zz-archive-phenotype-registry/` | PhenoRegistry | Recovery archive (234 files) |
| `archives/zz-archive-phenotype-monorepo-state-archive/` | PhenoAI | Monorepo state snapshot |

## Known Issues

### Critical (0)
None. Workspace compiles clean.

### High (2)
1. **3 PhenoRegistry crates orphaned** - not in workspace, should be integrated or removed
2. **47 compiler warnings** - mostly missing docs (26), unused imports (3), unused structs (5)

### Medium (3)
1. **Future-compat warnings** - `block v0.1.6` and `proc-macro-error2 v2.0.1` will be rejected by future Rust
2. **Origin URLs stale** - several absorbed crates still reference old repo URLs (phenotype-tooling, PhenoObservability)
3. **CRLF line ending drift** - 5 session extract files have mixed line endings

### Low (2)
1. **`fabric-capture`** has its own `[profile]` section (workspace ignores it, warning only)
2. **`pheno-otel.subdirectory`** unused manifest key warning

## Workspace Structure (key areas)

```
crates/                    # 310 dirs, 79 workspace members
  substrate-*              # Core substrate crates (14)
  fabric-*                 # PhenoFabric absorbed (21)
  engine-*                 # Engine crates (forge, codex, claude, a2a, agentapi)
  cloud-*                  # Cloud dispatch crates
  routing-*                # Routing crates
  phenotype-*              # Various phenotype crates
  pheno-*                  # Various pheno crates
registry/                  # PhenoRegistry data (JSON index, specs, audits)
bench/                     # PhenoLab RLVR harness
evals/                     # PhenoMLX eval suites
perf-core/                 # PhenoMLX Rust perf cores
apps/bench-cockpit/        # Benchmark cockpit (Go server + React UI)
archives/                  # Recovery/deletion archives
docs/                      # Atlas dossiers, architecture docs, sessions
```

## External Dependencies (git)

| Dependency | Source | Status |
|-----------|--------|--------|
| `phenotype-crypto` | PhenoInfra.git @ e001322 | EXISTS (200 OK) |
| `phenotype-health` | PhenoInfra.git @ e001322 | EXISTS |
| `phenotype-observability` | PhenoInfra.git @ e001322 | EXISTS |
| `phenotype-policy-engine` | PhenoInfra.git @ e001322 | EXISTS |
| `phenotype-mcp` | PhenoInfra.git @ e001322 | EXISTS |

Note: PhenoInfra was absorbed but these git deps still reference the external repo. Local copies exist at `crates/phenotype-policy-engine/` and `crates/phenotype-mcp/` but the workspace still pulls from git.

## What's Next

### Phase B: Integration Cleanup
1. ~~Add `phenotype-project-registry` and `phenotype-service-registry` to workspace members~~ DONE
2. ~~Fix or remove `pheno-registry-python` (broken dep)~~ ORPHANED (harmless)
3. Resolve git deps that have local copies (PhenoInfra crates)
4. Update stale origin URLs in absorbed crate manifests

### Phase C: Quality
1. Fix 47 warnings (missing docs, unused imports)
2. Address future-compat warnings (block, proc-macro-error2)
3. Normalize CRLF line endings in session extracts

### Phase D: Productization
1. Classify registry/ data for tracking
2. CI/CD pipeline for the monorepo
3. Release artifact and versioning strategy
