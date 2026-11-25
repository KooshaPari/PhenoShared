# Side-02 Audit: Hexagonal Architecture Ports

**Date:** 2026-06-19
**DAG task:** side-02 (FLEET_DAG_v3.db)
**Scope:** `pheno` monorepo — hexagonal ports/ trait directories

## Summary

3 ports/ directories found, defining **12 traits** across 13 files.
**No `adapters/` directory** in any pheno-* crate — adapters live in `agileplus-sqlite/ports/storage_port.rs` (a per-implementation file pattern, not a traditional `adapters/` folder).

## Inventory

### 1. `pheno/crates/phenotype-contracts/src/ports/` — 6 traits (CQRS-shaped)

| File | Trait | Methods |
|---|---|---|
| inbound.rs | `Command` | 0 (marker) |
| inbound.rs | `Query` | 0 (marker) |
| mod.rs | `UseCaseResult` | 0 (marker) |
| outbound.rs | `RepositoryPort` | 0 (marker) |
| outbound.rs | `CachePort` | 0 (marker) |
| outbound.rs | `SecretPort` | 0 (marker) |

**Pattern:** All marker traits (`trait X: Send + Sync {}`). CQRS-style separation
(inbound = commands/queries, outbound = ports). No methods on the traits
themselves — they're typed markers. Implementation methods come from impl blocks
in adapter crates.

### 2. `pheno/crates/agileplus-domain/src/ports/` — 6 traits (Domain ports)

| File | Trait | Methods |
|---|---|---|
| agent.rs | `AgentPort` | 5 |
| content.rs | `ContentStoragePort` | 21 |
| observability.rs | `ObservabilityPort` | 11 |
| review.rs | `ReviewPort` | 7 |
| storage.rs | `StoragePort` | 51 |
| vcs.rs | `VcsPort` | 11 |

**Pattern:** All traits `pub trait XPort: Send + Sync { ... }` with real method
signatures. `StoragePort` is the largest (51 methods) — likely a god-trait that
should be split per-aggregate (e.g., `WorkPackagePort`, `FeaturePort`,
`MetricPort`).

### 3. `pheno/crates/agileplus-sqlite/src/ports/` — adapter impls (not traits)

Files: `adapter.rs`, `content_storage.rs`, `mod.rs`, `storage_port.rs`

**Pattern:** This directory is the **adapter implementation**, not trait
definitions. `storage_port.rs` (24+ LOC) implements `agileplus_domain::ports::StoragePort`
for `SqliteStorageAdapter`. `content_storage.rs` likely does the same for
`ContentStoragePort`. The naming convention reverses the typical
`ports/{trait}.rs` pattern — here the trait file IS the implementation.

## Findings

### F1: StoragePort is a god-trait (51 methods)
`agileplus-domain/src/ports/storage.rs` defines 51 methods on `StoragePort`.
This violates ISP (Interface Segregation Principle). Recommendation: split
into per-aggregate traits:

- `WorkPackagePort` (WP state, dependencies, work logs)
- `FeaturePort` (features, state machine)
- `MetricPort` (metrics, aggregations)
- `GovernancePort` (policies, evidence, audit)
- `SyncMappingPort` (cross-repo sync)
- `ProjectPort` (project config)
- `ModulePort` (modules + feature tags)

### F2: Two incompatible ports/ patterns
- `phenotype-contracts/ports/` uses **CQRS marker traits** (Command, Query, ports).
- `agileplus-domain/ports/` uses **rich domain ports** (Agent, Storage, VCS).
- `agileplus-sqlite/ports/` uses **trait-named adapter files** (storage_port.rs).

These are not necessarily wrong, but they're inconsistent. A newcomer would be
confused by the three patterns.

### F3: No `adapters/` directory anywhere
The conventional hexagonal layout is `domain/ports/ + infra/adapters/`. Here
adapters are co-located with the trait impls in the same crate. This is fine
for small systems but blurs the boundary as the system grows.

### F4: `mod.rs` files have no `pub use` re-exports
`phenotype-contracts/src/ports/mod.rs` and `agileplus-domain/src/ports/mod.rs`
should re-export the traits for ergonomic imports
(`use crate::ports::Command;` vs `use crate::ports::inbound::Command;`).

## Recommendations

1. **Split StoragePort** into 6-7 per-aggregate traits (F1) — biggest win
2. **Add `pub use`** re-exports in `mod.rs` files (F4) — small win
3. **Document the three ports/ patterns** in `docs/architecture/hexagonal.md` (F2)
4. **Move adapters to `infra/adapters/`** once the monorepo grows past ~5 adapter
   implementations (F3) — not urgent

## Verification

- `grep -rE "^pub trait " pheno/crates/phenotype-contracts/src/ports/` → 6 hits
- `grep -rE "^pub trait " pheno/crates/agileplus-domain/src/ports/` → 6 hits
- `grep -rcE "fn " pheno/crates/agileplus-domain/src/ports/*.rs` → 106 total methods
- No `adapters/` directory under any `pheno/crates/*/src/`
