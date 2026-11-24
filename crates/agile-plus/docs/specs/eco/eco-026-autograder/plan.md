# Plan: Autograder Harness

## Objective
A single `make autograde` command that runs every gate the spec set requires and emits a per-FR pass/fail report.

## Scope
- A `xtask` binary in `AgilePlus/crates/agileplus-xtask` (or a Makefile wrapper if simpler)
- A JSON report writer
- CI wiring

## Implementation Steps
1. Scaffold `xtask` with subcommands: `build`, `test`, `clippy`, `trace`, `journey`, `spec-first`, `regression`, `report`.
2. Wire each subcommand to its underlying tool / script.
3. `report` aggregates the per-FR results into `worklogs/autograde-<date>.json`.
4. `make autograde` invokes `cargo run -p agileplus-xtask -- report`.
5. Add CI workflow `.github/workflows/autograde.yml` on every PR.
6. Add unit tests in `agileplus-xtask`.

## Verification
- `make autograde` exits 0 on the live tree
- A sample report exists and lists every FR
- A deliberately-broken FR (e.g. delete a test) makes autograde exit non-zero
