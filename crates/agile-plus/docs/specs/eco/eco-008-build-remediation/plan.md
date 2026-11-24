# Plan: Build Remediation (eco-008)

## Objective
Resolve the 7 build issues documented in `worklogs/build-triage-20260605.json` (5 confirmed, 2 unconfirmed) so that `cargo check --workspace` succeeds across all affected repos without expanding disk usage.

## Scope
- 8 repos touched: phenoAI, OmniRoute, pheno, phenoUtils, NetScript, MCPForge, phenoData, eyetracker.
- 7 work packages (WP-01..WP-07), see `tasks.md`.
- Reuses existing `repos/<repo>-wtrees/build-triage-<repo>/` worktrees; no new worktrees.

## Implementation Steps

### Pre-flight (all repos)
1. `df -h /Users/<REDACTED>` — confirm ≥ 20 GiB free. If below, skip `cargo check` and mark verification as deferred.
2. `git status --short --branch` in each affected worktree to confirm clean baseline.

### WP-01 phenoAI
- File: `repos/phenoAI-wtrees/build-triage-phenoAI/crates/llm-router/Cargo.toml` (line 13)
- Replace `features = ["json","rustls-tls"]` with `default-features = false, features = ["json","rustls","rustls-native-certs"]`.
- Verify: `cargo check -p llm-router` from `phenoAI/`.

### WP-02 OmniRoute
- File: `repos/crates/focus-always-on/Cargo.toml` (line 17)
- Choose path: (a) `git submodule add` PhenoObservability at `PhenoObservability/`, or (b) switch to published `phenotype-observably-macros = "x.y.z"`.
- Verify: `cargo check --workspace` from `repos/OmniRoute/`.

### WP-03 pheno
- File: `repos/pheno-wtrees/build-triage-pheno/crates/agileplus-domain/Cargo.toml` (line 19)
- Resolve the `../../../../../phenotype-shared/...` path: either add `phenotype-shared` as sibling repo/submodule, or vendor `phenotype-migrations` into `pheno/`.
- Verify: `cargo check --workspace` from `pheno/`.

### WP-04 phenoUtils
- File: `repos/phenoUtils-wtrees/build-triage-phenoUtils/crates/pheno-crypto/src/lib.rs` (line 66)
- Update imports: `use rand::Rng;` + `use rand::RngCore;` (or `rand_core::RngCore`); replace `rand::thread_rng()` with `rand::rng()`.
- Verify: `cargo check -p pheno-crypto`.

### WP-05 NetScript / MCPForge
- Both inherit the WP-02 path-dep. Apply the chosen WP-02 fix.
- If MCPForge is meant to be leaf-only, add its own `[workspace]` table to opt out of parent `repos/Cargo.toml`.
- Verify: `cargo check --workspace` from each repo root.

### WP-06 phenoData (unconfirmed)
- Re-run the originally reported command; capture full log.
- If `cargo check --workspace` is clean (as 2026-06-05 triage indicated), downgrade to "no-repro" with log evidence; add a runtime smoke test on `surreal-bridge` if the timeout surfaces at runtime.
- Verify: rerun command exits 0; log archived to `worklogs/`.

### WP-07 eyetracker (unconfirmed)
- Re-run the originally reported command; capture full log.
- If a uniffi binding manifest is required, scaffold `eyetracker-ffi` with `uniffi::include_scaffolding!` or `uniffi-bindgen` invocation; otherwise downgrade to "no-repro".
- Verify: rerun command exits 0; log archived.

## Verification
- Per-WP: `cargo check` exit code 0 captured in the WP notes.
- Per-repo: workspace-level `cargo check` from the repo root.
- Cross-repo: re-run `repos/worklogs/build-triage-20260605.json` reproduction commands; all 7 items must be green.
- Disk budget: pre/post `df -h` snapshots attached to the WP notes.
