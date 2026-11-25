---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05T00:00:00Z
last_audit: 2026-06-05
plan_status: REQUIRED
slug: eco-024-traceability
spec_id: eco-024
state: PENDING
status: active
superseded_by: null
title: Traceability Matrix
type: operational
---
# Specification: Traceability Matrix

## Problem Statement
The ecosystem tracks FRs in `FUNCTIONAL_REQUIREMENTS.md`, specs under
`AgilePlus/kitty-specs/`, tests in repo `tests/` trees, and journey stubs
under `docs/operations/journey-traceability.md`. There is no single document
that proves an FR is met end-to-end across spec -> docs -> tests -> code ->
journey. Auditors and agents must hand-grep five trees to answer "is FR-X
covered?" and the answer drifts as files move. The result is silent coverage
gaps: FRs without tests, tests without journeys, journeys without code.

## Target Users
- **Auditors / governance agents** who must prove an FR is implemented,
  tested, documented, and journey-traced in one hop.
- **Implementers** who need to know the existing coverage before adding a
  new artifact (so they do not duplicate or fork).
- **Dispatch coordinators** who need a machine-readable map to spawn the
  right worker for an FR gap.
- **Future agents** recovering context from a cold repo, who need a
  single index pointing to the spec anchor, docs pages, test paths, code
  modules, and journey stubs for every FR.

## Functional Requirements
- **FR-1**: Every FR in `FUNCTIONAL_REQUIREMENTS.md` MUST have a sibling
  `trace.json` file at `AgilePlus/traces/<fr_id>.json` describing its
  coverage across all five layers.
- **FR-2**: Each `trace.json` MUST conform to the schema:
  `{fr_id, spec_slug, spec_anchor, docs_pages: [paths], tests: [test_paths], code_modules: [paths], journeys: [stub_paths]}`.
  Every list MUST be present (empty list allowed) and every path MUST be
  repo-relative.
- **FR-3**: A `trace-validator` binary (in `tooling/trace-validator/`,
  Rust preferred per scripting policy) MUST walk all `trace.json` files
  and fail the build on: missing fields, malformed paths, dangling
  references, or any FR in `FUNCTIONAL_REQUIREMENTS.md` lacking a trace.
- **FR-4**: CI MUST run `trace-validator` on every PR and block merge on
  any traceability gap. The same gate runs in the autograder.
- **FR-5**: A generated `AgilePlus/traces/MATRIX.md` MUST render a
  human-readable row per FR (FR-ID, spec, docs, tests, code, journeys,
  green/yellow/red status) and be regenerated on every validator pass.
- **FR-6**: Journey stubs MUST live under
  `docs/operations/journeys/<fr_id>.md` with frontmatter linking back to
  the FR; the `journeys` list in `trace.json` points to those files.
- **FR-7**: A `--check-anchors` mode MUST verify that `spec_anchor`
  matches a real heading in the named `spec_slug`'s `spec.md` (no
  dangling anchors).
- **FR-8**: The trace schema and validator MUST be versioned in
  `AgilePlus/traces/SCHEMA.md` so future changes are explicit.

## Acceptance Criteria
- The autograder confirms no FR in `FUNCTIONAL_REQUIREMENTS.md` lacks a
  complete `trace.json` (FR-1, FR-2).
- The autograder runs `trace-validator` and confirms exit 0 on a
  reference corpus of 10+ FRs (FR-3).
- A CI workflow (`agileplus-traceability.yml`) is present and the
  autograder invokes it (FR-4).
- `MATRIX.md` is generated and lists every FR with a non-empty row
  (FR-5).
- At least one journey stub is created and linked from a trace (FR-6).
- A dangling `spec_anchor` in a test trace causes validator failure
  (FR-7).
- `SCHEMA.md` exists and matches the JSON shape in FR-2 (FR-8).

## Constraints & Dependencies
- Rust preferred for `trace-validator` per the Phenotype scripting
  language hierarchy; Python wrapper allowed only for glue.
- Disk is full during the writing window: write files only, no git,
  no worktrees, no CI runs.
- Traceability must not retroactively block already-merged FRs; the
  first run backfills missing traces with `status: pending-review`.
- Schema changes require bumping `SCHEMA.md` version and re-running
  the validator.
- All paths in `trace.json` are repo-relative POSIX; no absolute
  paths, no `~/` shortcuts.
