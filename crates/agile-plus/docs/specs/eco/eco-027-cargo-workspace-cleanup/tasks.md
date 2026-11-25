# Tasks: Cargo Workspace Cleanup

## WP-01: Inventory + classify
**Effort:** S
- [ ] T001 — Author `scripts/inventory-path-deps.py`.
- [ ] T002 — Run on the live tree; produce `AgilePlus/traces/cargo-deps.json`.

## WP-02: Resolve missing deps
**Effort:** M
- [ ] T003 — For each `missing` dep, decide the policy in the per-FR trace.
- [ ] T004 — Implement the chosen policy (publish, extract, or stub).
- [ ] T005 — Confirm `cargo build --workspace` exits 0.

## WP-03: CI gate
**Effort:** S
- [ ] T006 — `make cargo-audit` target.
- [ ] T007 — Wire into CI (`.github/workflows/cargo-audit.yml`).
- [ ] T008 — Required check on `main`.

## WP-04: Verification
**Effort:** S
- [ ] T009 — Run on a fixture tree with a broken `path = "..."`; confirm CI fails.
