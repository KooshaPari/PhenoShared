# Tasks: Traceability Matrix

## WP-01: Trace schema + indexer
**Effort:** S
- [ ] T001 — Publish `kitty-specs/trace.schema.json` with required FR/NFR fields.
- [ ] T002 — Author `scripts/build-trace-index.py` walking every active spec.
- [ ] T003 — Generate `kitty-specs/trace.index.json` from current 16 active specs.

## WP-02: Per-FR trace.json backfill
**Effort:** M
- [ ] T004 — Backfill `trace.json` for each of the 16 active specs (eco-007..022).
- [ ] T005 — For each FR, attach at least one docs page, one test, and (where applicable) a journey stub.
- [ ] T006 — Mark FRs without tests as NFR-only or scope-cut to MVP for the next pass.

## WP-03: CI gate
**Effort:** S
- [ ] T007 — Add `make trace-check` to the AgilePlus Makefile.
- [ ] T008 — Wire `trace-check` into `autograder` (eco-026) as a required step.
- [ ] T009 — Add a pre-merge hook that fails if any FR loses a trace entry.

## WP-04: Verification
**Effort:** S
- [ ] T010 — Run `make trace-check` against the live tree; confirm 0 missing.
- [ ] T011 — Document the trace contract in `AgilePlus/docs/traceability.md`.
