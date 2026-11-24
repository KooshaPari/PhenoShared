# Plan: Traceability Matrix

## Objective
Bind every FR in every active spec to its docs, tests, code, and journey capture so a single CI step proves the feature is met end-to-end.

## Scope
- Trace schema and per-FR `trace.json` files
- A walkable aggregate `trace.index.json`
- A CI step that verifies every entry

## Implementation Steps
1. **Schema** — Publish `kitty-specs/trace.schema.json` with required fields.
2. **Per-FR trace** — Add a `trace.json` next to every spec under `kitty-specs/<slug>/trace.json`.
3. **Indexer** — `scripts/build-trace-index.py` walks every spec, resolves every FR anchor, emits `trace.index.json`.
4. **CI step** — `make trace-check` validates the index, every file path, every test existence.
5. **Backfill** — Per eco-023 MVP-then-mature, do a backfill pass over the 16 active specs to seed the trace.

## Verification
- `make trace-check` exits 0
- `trace.index.json` lists every FR from every active spec
- A pre-merge hook refuses any change that drops a trace entry
