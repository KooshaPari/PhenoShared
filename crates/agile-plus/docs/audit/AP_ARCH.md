# AgilePlus Hexagonal / SOLID Architecture Audit

> **Date:** 2026-06-14  
> **Scope:** Domain + Application crates (`agileplus-domain`, `agileplus-application`, `agileplus-events`, `agileplus-triage`, `agileplus-graph`, `agileplus-proto`, `agileplus-config`, `agileplus-validate`, `agileplus-fixtures`) plus adapter/interface layers where violations are severe.  
> **Method:** Direct source file inspection (grep/read). No builds, tests, or git operations performed.

---

## 1. Executive Summary

| Category | Count | Severity |
|----------|-------|----------|
| I/O deps in domain/application crates | 8 | High |
| Adapter logic leaking into domain/application | 4 | High |
| God-modules (SRP / ISP violations) | 6 | Medium |
| CLI directly bypassing application layer | 12 | Medium |

**Key Finding:** `agileplus-events` (a domain-support crate) depends on `tokio` in production code. `agileplus-application` transitively pulls `sqlx` through `agileplus-triage` even though `sqlx` is unused in the triage source. The `StoragePort` trait in `agileplus-domain` is a god-trait with ~80 methods covering 12+ sub-domains, violating the Interface Segregation Principle.

---

## 2. I/O Dependencies in Domain / Application Crates

Per hexagonal architecture, domain and application crates must be **pure Rust** — no `tokio`, `axum`, `sqlx`, `rusqlite`, `reqwest`, `ureq`, `gix`, `async-nats`, or `tonic` imports in production code.

### 2.1 `tokio` in production dependencies

| File | Line | Violation | Fix |
|------|------|-----------|-----|
| `crates/agileplus-events/Cargo.toml` | 16 | `tokio = { workspace = true }` in `[dependencies]` (not just `[dev-dependencies]`) | Move to `[dev-dependencies]` only; remove `tokio::sync::RwLock` from production code (see below) |
| `crates/agileplus-events/src/store.rs` | 7 | `use tokio::sync::RwLock;` in production `InMemoryEventStore` | Replace with `std::sync::Mutex` or `parking_lot::RwLock` (both are sync and do not require an async runtime) |
| `crates/agileplus-events/src/snapshot.rs` | 8 | `use tokio::sync::RwLock;` in production `InMemorySnapshotStore` | Replace with `std::sync::Mutex` or `parking_lot::RwLock` |
| `crates/agileplus-application/Cargo.toml` | 20 | `tokio = { workspace = true, features = ["full"] }` in `[dependencies]` | Move to `[dev-dependencies]`; the only `tokio::sync::RwLock` usage is inside `#[cfg(test)]` blocks (`lib.rs:29`, `use_cases/persist_synced_stories.rs:119`) |
| `crates/agileplus-graph/Cargo.toml` | 12 | `tokio = { workspace = true }` in `[dependencies]` | Move to `[dev-dependencies]`; the only tokio references are `#[tokio::test]` inside `graph_store.rs` |
| `crates/agileplus-triage/Cargo.toml` | 28 | `tokio.workspace = true` in `[dependencies]` | **Remove entirely** — zero `tokio::` references in the triage source tree |

### 2.2 `sqlx` declared but unused

| File | Line | Violation | Fix |
|------|------|-----------|-----|
| `crates/agileplus-triage/Cargo.toml` | 33 | `sqlx.workspace = true` in `[dependencies]` | **Remove entirely** — zero `sqlx` references in the triage source tree. This is a transitive leak because `agileplus-application` depends on `agileplus-triage`, forcing `sqlx` into the application layer dependency graph. |

### 2.3 `tonic` / `prost` in a crate misclassified as domain core

| File | Line | Violation | Fix |
|------|------|-----------|-----|
| `crates/agileplus-proto/Cargo.toml` | 14 | `tonic.workspace = true` | Reclassify `agileplus-proto` in `Cargo.toml` comments and workspace docs from **"Domain & Application core"** to **"Infrastructure adapters (transport / surface)"**. The crate contains `tonic::async_trait`, `tonic::server::NamedService`, and `tokio_stream` types (`src/stubs.rs:389`, `src/stubs.rs:423`, `src/stubs.rs:464`). |
| `crates/agileplus-proto/Cargo.toml` | 15 | `prost.workspace = true` | Same as above |
| `crates/agileplus-proto/Cargo.toml` | 16 | `tokio-stream.workspace = true` | Same as above |

### 2.4 HTTP client (`ureq`) in application layer

| File | Line | Violation | Fix |
|------|------|-----------|-----|
| `crates/agileplus-triage/Cargo.toml` | 37 | `ureq = { version = "2", optional = true, ... }` (feature-gated) | This is acceptable *only* if the embedding backends are considered infrastructure. However, the `embed` trait is defined in the triage crate, and the HTTP call is made inside the application logic. **Fix:** Move `OaiEmbeddings` and `VoyageEmbeddings` into a new `agileplus-embeddings-oai` adapter crate, or at least into a separate `adapters/` module within `agileplus-triage` so the core `EmbeddingBackend` trait remains pure. |

---

## 3. Adapter Logic Leaking into Domain / Application

### 3.1 Direct filesystem I/O in application use-case

| File | Line | Violation | Fix |
|------|------|-----------|-----|
| `crates/agileplus-application/src/use_cases/triage.rs` | 189 | `std::path::Path::new(root)` + `p.is_dir()` | Delegate to a `FsPort` or `RepoScannerPort` trait in `agileplus-domain/src/ports.rs` and implement it in `agileplus-sqlite` or a new `agileplus-fs` adapter. |
| `crates/agileplus-application/src/use_cases/triage.rs` | 215 | `std::path::Path::new(&req.cwd)` + `p.is_dir()` | Same as above. |

### 3.2 Direct HTTP calls in application logic

| File | Line | Violation | Fix |
|------|------|-----------|-----|
| `crates/agileplus-triage/src/embeddings.rs` | 225 | `ureq::post(&url)` inside `OaiEmbeddings::embed()` | Move to an adapter crate or module. The `EmbeddingBackend` trait should remain pure; the HTTP execution belongs in an infrastructure adapter. |
| `crates/agileplus-triage/src/embeddings.rs` | 302 | `ureq::post(&url)` inside `VoyageEmbeddings::embed()` | Same as above. |

### 3.3 CLI commands directly using `rusqlite` (bypassing application layer)

The `agileplus-cli` crate (interface layer) contains **12 command files** that directly construct `rusqlite::Connection` and execute raw SQL. This is an adapter leak into the interface layer — the CLI should invoke application services, not open database connections.

| File | Lines | Direct `rusqlite` usage count |
|------|-------|-------------------------------|
| `crates/agileplus-cli/src/commands/worklog.rs` | 23, 750, 761, 809, 833 | 5 |
| `crates/agileplus-cli/src/commands/trace.rs` | 39, 249, 298 | 3 |
| `crates/agileplus-cli/src/commands/import_dagctl.rs` | 82, 263 | 2 |
| `crates/agileplus-cli/src/commands/gate_run.rs` | 28, 160, 220 | 3 |
| `crates/agileplus-cli/src/commands/gate_add.rs` | 17, 96, 106, 131, 148 | 5 |
| `crates/agileplus-cli/src/commands/dashboard.rs` | 42, 238, 260, 289, 486, 514 | 6 |
| `crates/agileplus-cli/src/commands/sidecar_status.rs` | 23, 175, 218, 233 | 4 |
| `crates/agileplus-cli/src/commands/seed_requirements.rs` | 39, 132 | 2 |
| `crates/agileplus-cli/src/commands/scope_status.rs` | 26, 202, 229, 258 | 4 |
| `crates/agileplus-cli/src/commands/run_record.rs` | 5, 19, 118, 136, 180, 210 | 6 |

**Fix:** For each command, replace `rusqlite::Connection::open(...)` with a `StoragePort` or `StoryRepository` obtained from the application layer, and move the SQL logic into `agileplus-sqlite` where it belongs.

---

## 4. God-Modules (SRP / ISP Violations)

A module is classified as a "god-module" when it exceeds ~400 lines, contains >25 functions, or mixes unrelated responsibilities.

### 4.1 Domain Layer

| File | Lines | Structs | Impls | Functions | Traits | Issue | Fix |
|------|-------|---------|-------|-----------|--------|-------|-----|
| `crates/agileplus-domain/src/ports.rs` | 527 | 2 | 4 | 130 | 5 | `StoragePort` trait has ~80 methods covering Features, Work Packages, Audit, Evidence, Policy, Modules, Cycles, Sync Mappings, Projects, Users, Epics, Stories. Violates ISP. | Split `StoragePort` into focused sub-traits: `FeatureRepository`, `WorkPackageRepository`, `AuditRepository`, `EvidenceRepository`, `PolicyRepository`, `ModuleRepository`, `CycleRepository`, `SyncMappingRepository`, `ProjectRepository`, `UserRepository`, `EpicRepository`, `StoryRepository` (the last two already exist as separate files). The existing `StoragePort` can become a *composite* trait that requires all sub-traits for adapter convenience. |
| `crates/agileplus-domain/src/ports.rs` | 527 | 2 | 4 | 130 | 5 | Also defines `ContentStoragePort` (~20 methods), `VcsPort` (~15 methods), `TriagePort` (2 methods), `TriageError`, `TriageTicket`, `TriageOutcome`, `ReviewPort`, and blanket impls for `StoryRepository` and `EpicRepository` — all in one file. | Move each trait + its error types to a dedicated module under `ports/`. The existing `ports/agent.rs`, `ports/epic.rs`, etc. are already small; apply the same pattern to the god-traits defined inline in `ports.rs`. |

### 4.2 Application Layer

| File | Lines | Structs | Impls | Functions | Traits | Issue | Fix |
|------|-------|---------|-------|-----------|--------|-------|-----|
| `crates/agileplus-application/src/lib.rs` | 1,008 | 4 | 5 | 98 | 0 | 100% of tests are embedded in a single `#[cfg(test)] mod tests` block inside `lib.rs`. | Move tests to `tests/` directory or `src/tests/` sub-modules (e.g., `tests/feature_tests.rs`, `tests/story_tests.rs`). |
| `crates/agileplus-triage/src/embeddings.rs` | 472 | 9 | 8 | 40 | 1 | Handles OaiEmbeddings, VoyageEmbeddings, LocalMockEmbeddings, cosine similarity, normalization, dimension validation, and HTTP request building in one file. | Split into `embeddings/backend.rs` (trait), `embeddings/local.rs`, `embeddings/oai.rs`, `embeddings/voyage.rs`, and `embeddings/math.rs` (cosine / norm). |
| `crates/agileplus-triage/src/bloom.rs` | 411 | 1 | 1 | 31 | 0 | Single `BloomFilter` struct with 31 methods: hash functions, bit-vector operations, serialization, optimal-parameter computation, and membership tests. | Extract `optimal_m`, `optimal_k`, `hash_family`, and `serialize`/`deserialize` into helper modules. Keep the core `BloomFilter` struct thin. |
| `crates/agileplus-triage/src/hybrid_pipeline.rs` | 564 | 4 | 4 | 27 | 0 | Combines MinHash-LSH candidate generation, embedding cosine verification, Jaccard tiebreak, and dup-group construction in one pipeline. | Split into `hybrid_pipeline/candidates.rs` (LSH), `hybrid_pipeline/verify.rs` (embedding), `hybrid_pipeline/tiebreak.rs` (Jaccard), and `hybrid_pipeline/group.rs` (DupGroup). |
| `crates/agileplus-triage/src/adapter.rs` | 373 | 4 | 4 | 29 | 1 | Orchestrates classifier, backlog store, dedup, claim, and router in one file. | Split into `adapter/classify.rs`, `adapter/backlog.rs`, `adapter/dedup.rs`, `adapter/claim.rs`, `adapter/router.rs`. |

### 4.3 Adapter Layer

| File | Lines | Structs | Impls | Functions | Traits | Issue | Fix |
|------|-------|---------|-------|-----------|--------|-------|-----|
| `crates/agileplus-sqlite/src/lib.rs` | 2,204 | 1 | 4 | 179 | 0 | Implements `StoragePort`, `ContentStoragePort`, and `EventStore` for a single `SqliteStorageAdapter` struct. All 179 methods are thin delegations, but the file is still a compilation bottleneck. | Keep the composite impls in `lib.rs` but move each delegation group to its own file under `src/storage/` (e.g., `storage/feature.rs`, `storage/work_package.rs`, `storage/audit.rs`). The `conn_for_bench()` method (line 103) exposes raw `rusqlite::Connection` and should be removed or gated behind `#[cfg(test)]` — it breaks the port abstraction. |

---

## 5. Dependency Transitivity Map

```
agileplus-cli
  ├── agileplus-application        [tokio in deps, but test-only usage]
  │   ├── agileplus-triage          [tokio UNUSED, sqlx UNUSED, ureq in deps]
  │   ├── agileplus-graph          [tokio in deps, but test-only usage]
  │   └── agileplus-domain         [CLEAN]
  ├── agileplus-sqlite             [adapter — ok]
  ├── agileplus-github             [adapter — ok]
  └── rusqlite                     [adapter leak: CLI uses it directly]

agileplus-events
  ├── tokio                        [PRODUCTION DEP — violation]
  └── agileplus-domain             [CLEAN]

agileplus-proto
  ├── tonic                        [misclassified as domain]
  ├── prost                        [misclassified as domain]
  └── tokio-stream                 [misclassified as domain]
```

---

## 6. Recommended Fix Priority

1. **High** — Remove `tokio` from `agileplus-events` production code (`store.rs`, `snapshot.rs`). This is the most severe violation because it forces an async runtime into a domain-support crate.
2. **High** — Remove unused `sqlx` and `tokio` from `agileplus-triage/Cargo.toml`. Run `cargo machete` to confirm and clean up.
3. **High** — Move `tokio` from `[dependencies]` to `[dev-dependencies]` in `agileplus-application` and `agileplus-graph`.
4. **High** — Refactor `StoragePort` in `agileplus-domain/src/ports.rs` into ISP-compliant sub-traits.
5. **Medium** — Replace direct `std::path::Path::is_dir()` calls in `agileplus-application/src/use_cases/triage.rs` with a port trait.
6. **Medium** — Move `OaiEmbeddings` and `VoyageEmbeddings` HTTP calls out of `agileplus-triage/src/embeddings.rs` into an adapter crate or module.
7. **Medium** — Break down god-modules (`embeddings.rs`, `bloom.rs`, `hybrid_pipeline.rs`, `adapter.rs`, `agileplus-sqlite/src/lib.rs`).
8. **Low** — Reclassify `agileplus-proto` in workspace documentation.
9. **Low** — Refactor `agileplus-cli` commands to use application-layer ports instead of direct `rusqlite`.

---

## 7. Files with Zero Violations (Clean)

- `crates/agileplus-config/src/` — no I/O deps
- `crates/agileplus-validate/src/` — no I/O deps
- `crates/agileplus-fixtures/src/` — no I/O deps
- `crates/agileplus-domain/src/` — no I/O deps (only `#[tokio::test]` in dev-only tests)

---

*End of audit.*
