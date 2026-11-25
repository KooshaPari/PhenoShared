# Tasks: Autograder Harness

## WP-01: xtask scaffold
**Effort:** S
- [ ] T001 — Add `crates/agileplus-xtask` to the workspace.
- [ ] T002 — Define `Autograde` subcommand skeleton.

## WP-02: Gate subcommands
**Effort:** M
- [ ] T003 — `build` subcommand: `cargo build --workspace`.
- [ ] T004 — `test` subcommand: `cargo test --workspace`.
- [ ] T005 — `clippy` subcommand: `cargo clippy --workspace --all-targets -- -D warnings`.
- [ ] T006 — `trace` subcommand: invoke `scripts/build-trace-index.py` and `make trace-check`.
- [ ] T007 — `journey` subcommand: lint docs for journey-stub presence.
- [ ] T008 — `spec-first` subcommand: verify every PR diff touches at least one `AgilePlus/kitty-specs/*/`.
- [ ] T009 — `regression` subcommand: walk trace history, fail if any MVP FR loses a previously-green test.

## WP-03: Report aggregation
**Effort:** S
- [ ] T010 — `report` subcommand writes `worklogs/autograde-<date>.json` with per-FR pass/fail.
- [ ] T011 — Make report deterministic (sort FRs, sort gates).

## WP-04: CI
**Effort:** S
- [ ] T012 — `.github/workflows/autograde.yml` runs on every PR.
- [ ] T013 — Required check on `main`; non-zero exits fail the PR.

## WP-05: Tests
**Effort:** S
- [ ] T014 — `agileplus-xtask` unit tests covering report generation.
- [ ] T015 — Integration test that runs autograde against a fixture tree.
