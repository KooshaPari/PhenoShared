# AgilePlus Dependency Audit — `docs/audit/AP_DEPS.md`

> Audit date: 2026-06-14  
> Scope: all `Cargo.toml` files in the repo (35 files). Read-only; no `cargo` commands executed.  
> Method: heuristic grep for source references (`use`, `::`, `extern crate`, derive macros) in `*.rs` files.

---

## 1. Version Skew

Dependencies that appear in multiple crates with **different semver versions** (not just different manifest notation).

| Dependency | Workspace Version | Crate(s) with Different Version | File:Line |
|------------|-------------------|-----------------------------------|-----------|
| `reqwest` | `0.12` | `agileplus-plane` uses `0.13` | `crates/agileplus-plane/Cargo.toml:18` |
| `thiserror` | `2` | `agileplus-governance` uses `1` | `crates/agileplus-governance/Cargo.toml:50` |
| `tracing-opentelemetry` | `0.27` | `agileplus-telemetry` uses `0.28` | `crates/agileplus-telemetry/Cargo.toml:14` |
| `uuid` | `1` | `agileplus-benchmarks` uses `1.10` | `crates/agileplus-benchmarks/Cargo.toml:19` |
| `uuid` | `1` | `agileplus-p2p` uses `1.10` | `crates/agileplus-p2p/Cargo.toml:29` |

**Notes:**
- `reqwest` is split across the workspace: `0.12` in `agileplus-github`, `agileplus-integration-tests`, and `agileplus-governance`; `0.13` in `agileplus-plane`.
- `agileplus-telemetry` bypasses the workspace `tracing-opentelemetry = "0.27"` (`Cargo.toml:143`) and pins `0.28` directly.
- `agileplus-governance` does not use `workspace = true` for `thiserror`, `serde`, `serde_json`, `chrono`, `tracing-subscriber`, `tokio`, `anyhow`, `tracing`, `rusqlite`, `config`, `regex`, `async-trait`, etc., creating a local version island.

---

## 2. Declared-but-Unused Dependencies (Heuristic Grep)

Deps declared in `Cargo.toml` but with **zero source references** in the corresponding crate's `*.rs` files (or across the workspace where noted). Macro-only crates (e.g. `serde` derive, `thiserror` derive) are excluded from this list because they are consumed via `#[derive(...)]` and do not always appear in `use` statements.

| Crate | Unused Dependency | Manifest File:Line | Notes |
|-------|-------------------|-------------------|-------|
| **workspace** | `sqlx` | `Cargo.toml:148` | Zero `use sqlx` / `sqlx::` across **entire repo**; only appears in comments (`crates/agileplus-application/src/lib.rs:4`, `crates/agileplus-application/src/error.rs:3`). Also declared in `agileplus-triage/Cargo.toml:33` with no source usage. |
| `agileplus-governance` | `envsubst` | `crates/agileplus-governance/Cargo.toml:60` | Zero references anywhere in `crates/agileplus-governance/`. |
| `agileplus-cli` | `tokio-test` | `crates/agileplus-cli/Cargo.toml:33` | Declared as dev-dependency; no `tokio-test` references in `crates/agileplus-cli/` (no `tests/` directory). |
| `agileplus-governance` | `tokio-test` | `crates/agileplus-governance/Cargo.toml:64` | Declared as dev-dependency; no `tokio-test` references in `crates/agileplus-governance/`. |
| `agileplus-sync` | `proptest` | `crates/agileplus-sync/Cargo.toml:30` | Dev-dependency with no `proptest` references; no `tests/` directory in the crate. |
| **root** (`agileplus`) | `cucumber` | `Cargo.toml:111` | Dev-dependency with zero references; no `tests/` directory at workspace root. |
| **root** (`agileplus`) | `sha2` | `Cargo.toml:112` | Dev-dependency with zero references at root; other crates consume it via workspace. |
| `agileplus-contract-tests` | **all regular deps** | `crates/agileplus-contract-tests/Cargo.toml:13-25` | `src/lib.rs` is a stub (11 lines of doc comments, no imports). Referenced test paths (`../../tests/contracts/...`) do **not exist**. Dependencies: `agileplus-domain`, `agileplus-events`, `agileplus-sqlite`, `agileplus-plane`, `agileplus-api`, `axum`, `serde`, `serde_json`, `chrono`, `tokio`, `thiserror`, `anyhow`, `tracing`. |
| **root** (`agileplus`) | **all regular deps** | `Cargo.toml:98-106` | `src/lib.rs` is a 2-line stub. No source code consumes `serde`, `serde_json`, `tokio`, `thiserror`, `anyhow`, `tracing`, `axum`, `chrono`. |

**Counts:**
- **1** workspace-level dependency with zero usage: `sqlx`.
- **3** dev-dependencies with zero usage across the workspace: `cucumber`, `tokio-test`, `sha2` (root-only).
- **2** regular dependencies with zero usage in their crate: `envsubst`, `sqlx` (in `agileplus-triage`).
- **1** crate (`agileplus-contract-tests`) where **all** declared regular deps are unused because the crate has no implementation or tests.
- **1** crate (`agileplus`, root) where **all** declared regular deps are unused because the package is a workspace stub.

---

## 3. `cargo-machete` Ignored List — Stale Entries

Root `Cargo.toml` `workspace.metadata.cargo-machete.ignored` (`Cargo.toml:158-159`) contains 21 entries.

### Stale / Questionable Ignores

| Ignored Dep | Reason | Status |
|-------------|--------|--------|
| `cucumber` | **Not present in `workspace.dependencies`**. Only appears as a root dev-dependency (`Cargo.toml:111`). No crate in the workspace uses it via `.workspace = true`. | **Stale** |
| `axum-test` | **Not present in `workspace.dependencies`**. Only appears as root dev-dependency (`Cargo.toml:109`) and `agileplus-api` dev-dependency (`crates/agileplus-api/Cargo.toml:42`). No crate uses it via `.workspace = true`. | **Stale** |
| `tracing-opentelemetry` | Present in `workspace.dependencies` at `0.27` (`Cargo.toml:143`), but **no crate uses it via `.workspace = true`**. `agileplus-telemetry` pins `0.28` directly (`crates/agileplus-telemetry/Cargo.toml:14`). The workspace entry is effectively orphaned. | **Stale / Orphaned** |

### Verified Non-Stale Ignores

The remaining 18 entries are **actively used** by at least one crate via `.workspace = true` or `.workspace = true` (build-dependencies):

- `paste` → `agileplus-config`
- `dirs` → `agileplus-telemetry`
- `serde_yaml` → `agileplus-api`, `agileplus-telemetry`, `xdd-lib-rs`
- `uuid` → `agileplus-benchmarks`, `agileplus-events`, `agileplus-p2p`, `agileplus-governance`, `agileplus-graph`, `agileplus-nats`, `agileplus-subcmds`
- `async-trait` → `agileplus-api`, `agileplus-application`, `agileplus-artifacts`, `agileplus-cache`, `agileplus-cli`, `agileplus-dashboard`, `agileplus-domain`, `agileplus-events`, `agileplus-git`, `agileplus-github`, `agileplus-grpc`, `agileplus-nats`, `agileplus-plane`, `agileplus-sqlite`, `agileplus-sync`, `agileplus-triage`
- `tracing-subscriber` → `agileplus-api`, `agileplus-cli`, `agileplus-dashboard`, `agileplus-telemetry`, `agileplus-integration-tests`, `agileplus-governance`
- `tracing-appender` → `agileplus-telemetry`
- `futures` → `agileplus-p2p`
- `futures-util` → `agileplus-p2p`, `agileplus-integration-tests`, `agileplus-sync`
- `tonic` → `agileplus-grpc`, `agileplus-proto`, `rust/Cargo.toml`
- `tonic-build` → `agileplus-grpc`, `agileplus-proto`, `rust/Cargo.toml`
- `prost` → `agileplus-proto`, `rust/Cargo.toml`
- `prost-build` → `agileplus-proto`
- `utoipa` → `agileplus-api`
- `opentelemetry` → `agileplus-telemetry`
- `opentelemetry_sdk` → `agileplus-telemetry`
- `opentelemetry-otlp` → `agileplus-telemetry`
- `gix` → `agileplus-git`
- `tempfile` → `agileplus-cli`, `agileplus-git`, `agileplus-governance`, `agileplus-p2p`, `agileplus-plane`, `agileplus-subcmds`, `agileplus-trace-validator`, `agileplus-telemetry`, `xdd-lib-rs`

---

## 4. Summary

- **4 version skews** found (reqwest, thiserror, tracing-opentelemetry, uuid).
- **7+ unused dependency declarations** found: `sqlx` (workspace-wide), `envsubst`, `tokio-test` (2 crates), `proptest`, `cucumber`, `sha2` (root dev-dep), and the entire dep set of `agileplus-contract-tests` and the root `agileplus` package.
- **3 stale machete ignores** (`cucumber`, `axum-test`, `tracing-opentelemetry`) out of 21 entries.
- **No-op crates with zero source consumption:** `agileplus-contract-tests` (stub lib, missing test files), root `agileplus` (2-line stub lib), and `pheno-ssot-template` (no deps, but valid lib).
