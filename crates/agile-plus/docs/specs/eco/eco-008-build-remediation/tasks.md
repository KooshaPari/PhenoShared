# Tasks: Build Remediation (eco-008)

## WP-01 phenoAI
- **Status:** PENDING
- **Worktree:** `repos/phenoAI-wtrees/build-triage-phenoAI/`
- **File:** `crates/llm-router/Cargo.toml` (line 13)
- **Root cause:** `reqwest` 0.13 removed `rustls-tls` feature.
- **Action:** Switch to `default-features = false, features = ["json","rustls","rustls-native-certs"]`.
- **Verify:** `cargo check -p llm-router` exits 0.
- **Disk floor:** ≥ 20 GiB free; defer verify if below.

## WP-02 OmniRoute
- **Status:** PENDING
- **Worktree:** `repos/OmniRoute-wtrees/build-triage-OmniRoute/`
- **File:** `crates/focus-always-on/Cargo.toml` (line 17)
- **Root cause:** Path-dep on missing `PhenoObservability` checkout.
- **Action:** Submodule/path-add `PhenoObservability` or migrate to published `phenotype-observably-macros`.
- **Verify:** `cargo check --workspace` exits 0.

## WP-03 pheno
- **Status:** PENDING
- **Worktree:** `repos/pheno-wtrees/build-triage-pheno/`
- **File:** `crates/agileplus-domain/Cargo.toml` (line 19)
- **Root cause:** Path-dep on missing `phenotype-shared` external workspace.
- **Action:** Add `phenotype-shared` as sibling or vendor `phenotype-migrations`.
- **Verify:** `cargo check --workspace` exits 0.

## WP-04 phenoUtils
- **Status:** PENDING
- **Worktree:** `repos/phenoUtils-wtrees/build-triage-phenoUtils/`
- **File:** `crates/pheno-crypto/src/lib.rs` (line 66)
- **Root cause:** `rand` 0.10 no longer re-exports `RngCore` / `thread_rng` from crate root.
- **Action:** Use `use rand::{Rng, RngCore};` and `rand::rng()`.
- **Verify:** `cargo check -p pheno-crypto` exits 0.

## WP-05 NetScript / MCPForge
- **Status:** PENDING
- **Worktrees:** `repos/NetScript-wtrees/build-triage-NetScript/`, `repos/MCPForge-wtrees/build-triage-MCPForge/`
- **File:** parent workspace `repos/crates/focus-always-on/Cargo.toml` (line 17)
- **Root cause:** Same WP-02 path-dep, inherited by both repos.
- **Action:** Apply WP-02 fix to parent workspace; MCPForge may opt out via its own `[workspace]` table.
- **Verify:** `cargo check --workspace` exits 0 in each repo.

## WP-06 phenoData (unconfirmed)
- **Status:** PENDING
- **Worktree:** `repos/phenoData-wtrees/build-triage-phenoData/`
- **File:** `crates/surreal-bridge/Cargo.toml` (line 14)
- **Root cause:** Reported `RocksDB timeout` did not reproduce on `cargo check --workspace` (3m 47s clean).
- **Action:** Re-run the originally reported failing command; capture full log. If no failure, downgrade to "no-repro" with log evidence; add runtime smoke test if timeout surfaces at runtime.
- **Verify:** Rerun command exits 0; log archived to `worklogs/`.

## WP-07 eyetracker (unconfirmed)
- **Status:** PENDING
- **Worktree:** `repos/eyetracker-wtrees/build-triage-eyetracker/`
- **File:** `bindings/` (line 1)
- **Root cause:** Reported "missing manifest" did not reproduce on `cargo check --workspace` (1m 18s clean).
- **Action:** Re-run the originally reported failing command; capture full log. If a uniffi binding manifest is required, scaffold `eyetracker-ffi` with `uniffi::include_scaffolding!`; otherwise downgrade to "no-repro".
- **Verify:** Rerun command exits 0; log archived.
