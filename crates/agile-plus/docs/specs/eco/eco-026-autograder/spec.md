---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
date: 2026-06-05
owner: repo-steward
plan_status: NOT_STARTED
retirement_criteria: `make autograde` exits 0 on the live tree; CI runs it on every PR; per-FR pass/fail report is published.
slug: eco-026-autograder
spec_id: eco-026
state: PENDING
status: active
superseded_by: null
title: Autograder Harness
type: operational
---
# Autograder Harness

## Problem
There is no single script that aggregates spec / docs / test / lint / journey gates and emits a per-FR pass/fail report. Reviewers currently run ad-hoc commands; specs can drift from tests without notice.

## Target Users
Repo stewards, CI reviewers, spec authors, downstream consumers.

## Functional Requirements
1. `make autograde` (or `cargo xtask autograde`) runs:
   1. `cargo build` and `cargo test` for the workspace.
   2. `cargo clippy --workspace --all-targets -- -D warnings`.
   3. `make trace-check` (eco-024).
   4. `make journey-stub-lint` (eco-022).
   5. `make spec-first-check` (eco-018 — every PR links a spec slug).
   6. `make fr-regression-check` (eco-023 — no MVP FR regressed).
2. Emits a per-FR report at `worklogs/autograde-<date>.json` with:
   `{generated_at, total_frs, passed, failed, fr_results: [{fr_id, spec_slug, gates: {build, test, clippy, trace, journey, regression}, status}]}`.
3. Non-zero exit code if any FR fails any gate.
4. Runs as a required CI step on every PR.
5. The autograder itself has tests (xtask tests in CI).

## Non-Functional Requirements
- Runs in < 15 minutes on the canonical CI runner
- UTF-8 no BOM
- Idempotent (re-running produces a stable report)

## Acceptance Criteria
- `make autograde` exits 0 on the live tree
- `worklogs/autograde-2026-06-05.json` lists every FR with a per-gate status
- PR CI fails when a gate fails

## Constraints
- Depends on eco-017 disk-recovery-gate
- Depends on eco-021 BDD/SDD/TDD/XDD
- Depends on eco-022 rich journey embeds
- Depends on eco-023 MVP-then-mature (fr-regression-check)
- Depends on eco-024 traceability matrix
