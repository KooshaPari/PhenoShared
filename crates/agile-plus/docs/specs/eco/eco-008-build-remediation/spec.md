---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
plan_status: NOT_STARTED
retirement_criteria: |
slug: eco-008-build-remediation
spec_id: eco-008
state: PENDING
status: active
superseded_by: null
title: Build Remediation
type: operational
---
# Specification: Build Remediation
**Slug**: eco-008-build-remediation | **Date**: 2026-06-05 | **State**: PENDING

## Problem
2026-06-05 build triage (`worklogs/build-triage-20260605.json`) identified 7 build issues across 8 repos:

**Confirmed (5):**
1. **phenoAI** — `crates/llm-router` enables removed `reqwest` 0.13 feature `rustls-tls`.
2. **OmniRoute** — `crates/focus-always-on` path-deps on `PhenoObservability/.../phenotype-observably-macros` (parent repo not checked out).
3. **pheno** — `agileplus-api` -> `agileplus-domain` -> path-dep on missing `phenotype-shared` external workspace.
4. **phenoUtils** — `crates/pheno-crypto` uses pre-0.10 `rand::RngCore` / `rand::thread_rng()` re-exports.
5. **NetScript** + **MCPForge** — inherit parent workspace containing the same broken `focus-always-on` path-dep (single root cause, two consumer repos).

**Unconfirmed (2):**
6. **phenoData** — reported `RocksDB timeout` did not reproduce; `cargo check --workspace` clean on HEAD of main.
7. **eyetracker** — reported "missing manifest" did not reproduce; `cargo check --workspace` clean on HEAD of main.

## Target Users
- CI maintainers
- Repo stewards across the Phenotype polyrepo
- Operators running local `cargo check`/`cargo build` work

## Functional Requirements
- **WP-01 phenoAI:** Replace `rustls-tls` feature on `reqwest` 0.13 with `default-features = false, features = ["json","rustls","rustls-native-certs"]` (or `rustls-webpki-roots`).
- **WP-02 OmniRoute:** Resolve missing `PhenoObservability` checkout — either git-submodule/path-add at `PhenoObservability/` or migrate `focus-always-on` to a published `phenotype-observably-macros` version.
- **WP-03 pheno:** Resolve missing `phenotype-shared` — sibling-repo layout, git submodule, or vendor `phenotype-migrations` into the workspace.
- **WP-04 phenoUtils:** Migrate `pheno-crypto` to rand 0.10 import paths (`use rand::Rng; use rand::RngCore;` and `rand::rng()`).
- **WP-05 NetScript / MCPForge:** Apply the WP-02 fix to the parent workspace; MCPForge additionally may opt-out of the parent workspace via its own `[workspace]` table.
- **WP-06 phenoData (unconfirmed):** Re-run the originally reported failing command; capture the actual log; if no failure, downgrade and add a regression check.
- **WP-07 eyetracker (unconfirmed):** Re-run the originally reported failing command; capture log; if a uniffi binding manifest is required, scaffold it; otherwise downgrade.

## Non-Functional Requirements
- `cargo check --workspace` must pass in each affected repo after the fix.
- No breaking API changes outside the modified crate.
- No new transitive dependency version pins without an entry in `DEPENDENCIES.md` worklog.

## Acceptance Criteria
- [ ] All 5 confirmed root causes resolved; `cargo check --workspace` exits 0.
- [ ] 2 unconfirmed root causes re-run with original commands and either resolved or downgraded with evidence.
- [ ] `build-triage-20260605.json` re-audit produces zero open findings for the seven items.
- [ ] Each WP records the changed file path + `cargo check` exit code in its notes.

## Constraints
- **Disk floor: ≥ 20 GiB free** before invoking `cargo build`/`cargo check`. Fall back to spec-only work (skip build verification) if below floor.
- No new git worktrees; disk is full. Author fixes in the existing `repos/<repo>-wtrees/build-triage-<repo>/` worktrees already present on disk.
- No commits authored by agents without explicit user instruction.
