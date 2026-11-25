# AgilePlus Deep Spec→Test→Code Traceability Audit

> File: `docs/audit/AP_TRACE_FULL.md`  
> Generated: 2026-06-14  
> Scope: Every FR listed in `FUNCTIONAL_REQUIREMENTS.md` (canonical registry, eco-034 in flight)  
> Method: Read-source grep (no builds, no git mutations)  
> Rating: FULL / PARTIAL / NONE

---

## Summary Roll-up

| FR ID | Title | Spec Anchor | Code Rating | Test Rating | Overall |
|-------|-------|-------------|-------------|-------------|---------|
| FR-024-1 | Per-FR `trace.json` mandatory | `kitty-specs/eco-024-traceability/spec.md:34-36` | PARTIAL | PARTIAL | PARTIAL |
| FR-024-2 | `trace.json` schema (5 layers) | `kitty-specs/eco-024-traceability/spec.md:37-41` | PARTIAL | PARTIAL | PARTIAL |
| FR-024-3 | `trace-validator` binary | `kitty-specs/eco-024-traceability/spec.md:42-45` | PARTIAL | PARTIAL | PARTIAL |
| FR-024-4 | CI gate on every PR | `kitty-specs/eco-024-traceability/spec.md:46-47` | NONE | NONE | NONE |
| FR-024-5 | `MATRIX.md` generated | `kitty-specs/eco-024-traceability/spec.md:48-50` | PARTIAL | NONE | NONE |
| FR-024-6 | Journey stubs under `docs/operations/journeys/<fr_id>.md` | `kitty-specs/eco-024-traceability/spec.md:51-53` | PARTIAL | NONE | PARTIAL |
| FR-024-7 | `--check-anchors` mode | `kitty-specs/eco-024-traceability/spec.md:54-56` | NONE | NONE | NONE |
| FR-024-8 | `SCHEMA.md` versioning | `kitty-specs/eco-024-traceability/spec.md:57-58` | PARTIAL | NONE | PARTIAL |

**Totals:** 8 FRs audited; 0 FULL, 5 PARTIAL, 3 NONE.

---

## FR-024-1 — Per-FR `trace.json` mandatory

**Spec:** `kitty-specs/eco-024-traceability/spec.md:34-36`  
**Trace:** `traces/FR-024-1.json` (exists, references non-existent test path)

### Code Modules
- `crates/agileplus-trace-validator/src/lib.rs:138-158` — `missing_requirements()` scans `FUNCTIONAL_REQUIREMENTS.md` and reports every FR-ID that lacks a sibling `traces/<fr_id>.json`. 2 trace files found with `fr_id` field.
- `crates/agileplus-trace-validator/src/lib.rs:42-95` — `validate_trace_path()` orchestrates the directory walk, JSON parsing, and path validation.
- `traces/FR-024-1.json` through `traces/FR-024-8.json` — 8 trace files exist (all have `fr_id` present).

### Tests
- `crates/agileplus-trace-validator/tests/cli.rs:7-16` — `validate_accepts_trace_directory` creates a temp repo with one trace and asserts `validated 1 trace files`.
- `crates/agileplus-trace-validator/tests/edge_cases.rs:131-173` — `stats_reports_multiple_traces` creates 3 traces and asserts `traces: 3`, indirectly covering multi-trace counting.
- `libs/xdd-lib-rs/src/lib.rs:304-327` — `json_to_yaml_agileplus_trace` uses `FR-024-1` as a dialect-conversion fixture, but does **not** test the trace-validator behavior.

### Gaps
- `trace.json` references `tooling/trace-validator/tests/spec.rs::test_fr1_trace_required` — file does not exist (`tooling/trace-validator/` directory missing). Actual crate is `crates/agileplus-trace-validator/`.
- No dedicated test named `test_fr1_trace_required` exists anywhere in the repo.

**Rating:** PARTIAL (code implements FR, tests exercise the path, but trace.json test path is dangling and no dedicated FR-024-1 test exists).

---

## FR-024-2 — `trace.json` schema (5 layers)

**Spec:** `kitty-specs/eco-024-traceability/spec.md:37-41`  
**Trace:** `traces/FR-024-2.json` (exists, references non-existent test path)

### Code Modules
- `crates/agileplus-trace-validator/src/lib.rs:97-116` — `read_trace()` validates required string fields (`fr_id`, `spec_slug`, `spec_anchor`) and required list fields (`docs_pages`, `tests`, `code_modules`, `journeys`). Hardcoded field checks at lines 103-113.
- `traces/SCHEMA.md:1-40` — documents the 5-layer schema (fr_id, spec_slug, spec_anchor, docs_pages, tests, code_modules, journeys, status, last_validated).

### Tests
- `crates/agileplus-trace-validator/tests/edge_cases.rs:59-81` — `validate_trace_missing_required_field_fails` asserts failure when `fr_id` is missing from a trace payload.
- `crates/agileplus-trace-validator/tests/edge_cases.rs:199-214` — `validate_malformed_json_array_payload_fails` asserts failure when top-level JSON is an array instead of the expected object shape.
- `crates/agileplus-trace-validator/tests/edge_cases.rs:43-54` — `validate_empty_payload_fails` asserts failure on zero-byte JSON file.
- `crates/agileplus-trace-validator/tests/edge_cases.rs:24-39` — `validate_malformed_json_trace_fails` asserts failure on truncated JSON.
- `crates/agileplus-trace-validator/tests/edge_cases.rs:178-193` — `validate_whitespace_only_payload_fails` asserts failure on whitespace-only payload.

### Gaps
- `trace.json` references `tooling/trace-validator/tests/spec.rs::test_fr2_schema_fields` — file does not exist.
- No test validates that all 5 layers are present as a single unit; tests cover individual field-level failures only.

**Rating:** PARTIAL (code validates schema, tests cover edge cases, but no dedicated schema-layer test and trace.json path is dangling).

---

## FR-024-3 — `trace-validator` binary

**Spec:** `kitty-specs/eco-024-traceability/spec.md:42-45`  
**Trace:** `traces/FR-024-3.json` (exists, references non-existent test path)

### Code Modules
- `crates/agileplus-trace-validator/src/main.rs:1-67` — CLI binary with `Validate`, `Graph`, `Stats`, `Missing` subcommands. Uses `clap` for argument parsing.
- `crates/agileplus-trace-validator/src/lib.rs:42-95` — `validate_trace_path()` library entrypoint.
- `crates/agileplus-trace-validator/src/lib.rs:24-40` — `TraceValidation` struct with `trace_count()` and `referenced_path_count()`.
- `crates/agileplus-trace-validator/Cargo.toml` — binary crate definition (exists, 5 source files, 2 test files).

### Tests
- `crates/agileplus-trace-validator/tests/cli.rs:7-16` — `validate_accepts_trace_directory` invokes the compiled binary via `assert_cmd` and checks success exit code.
- `crates/agileplus-trace-validator/tests/cli.rs:19-29` — `stats_prints_trace_counts` invokes binary and asserts `traces: 1` and `references: 4` in stdout.
- `crates/agileplus-trace-validator/tests/edge_cases.rs` — 8 additional edge-case tests (empty traces, malformed JSON, missing fields, etc.) all invoke the binary.

### Gaps
- `trace.json` references `tooling/trace-validator/tests/cli.rs::test_validator_runs` — file does not exist.
- The spec requires the validator to "fail the build on: missing fields, malformed paths, dangling references, or any FR lacking a trace". The code does this, but the binary is invoked in tests via `assert_cmd` only; there is no unit-test coverage of the library functions themselves.

**Rating:** PARTIAL (binary exists, CLI tests cover happy path and edge cases, but trace.json path is dangling and no unit tests for library functions).

---

## FR-024-4 — CI gate on every PR

**Spec:** `kitty-specs/eco-024-traceability/spec.md:46-47`  
**Trace:** `traces/FR-024-4.json` (exists, references non-existent workflow and test)

### Code Modules
- `.github/workflows/agileplus-traceability.yml` — **MISSING** (does not exist).
- `.github/workflows/fr-coverage.yml:1-18` — Stub workflow exists. It is triggered on `pull_request` but only runs `echo "FR coverage check (phenotype-tooling integration)"`. It does **not** invoke `agileplus-trace-validator` or enforce traceability.
- `.github/workflows/ci.yml` — CI workflow exists; no trace-validator invocation found inside.
- `.github/workflows/autograder.yml` — Autograder workflow exists; no trace-validator invocation found inside.

### Tests
- `trace.json` references `tooling/trace-validator/tests/ci.rs::test_ci_workflow_runs_validator` — file does not exist.
- No test in the repo validates that a CI workflow runs the trace-validator.

### Gaps
- Required workflow file is missing entirely.
- Existing `fr-coverage.yml` is a non-functional stub.
- No CI gate actually blocks merge on traceability gaps.

**Rating:** NONE (no implementing code, no tests, no CI gate).

---

## FR-024-5 — `MATRIX.md` generated

**Spec:** `kitty-specs/eco-024-traceability/spec.md:48-50`  
**Trace:** `traces/FR-024-5.json` (exists, references non-existent test and code module)

### Code Modules
- `crates/agileplus-trace-validator/src/main.rs:36-47` — `Graph` subcommand prints a simple TSV-like row per FR (`fr_id -> docs:N tests:N code:N journeys:N`). No `--emit-matrix` flag.
- `traces/MATRIX.md:1-21` — Hand-written stub exists; header says "This file is regenerated by `trace-validator --emit-matrix`. Until the validator is implemented, this is a hand-written seed."
- `crates/agileplus-trace-validator/src/graph.rs:1-82` — `TraceGraph` struct with `from_documents()` and `incoming_refs()`. Could be used for matrix generation, but no caller produces a markdown matrix.

### Tests
- `trace.json` references `tooling/trace-validator/tests/matrix.rs::test_matrix_renders_all_frs` — file does not exist.
- No test in the repo verifies MATRIX.md generation or `--emit-matrix` behavior.

### Gaps
- No `--emit-matrix` flag in the CLI.
- No automated generation of `MATRIX.md`.
- No dedicated test for matrix rendering.

**Rating:** NONE (no generation code, no tests; hand-written stub only).

---

## FR-024-6 — Journey stubs under `docs/operations/journeys/<fr_id>.md`

**Spec:** `kitty-specs/eco-024-traceability/spec.md:51-53`  
**Trace:** `traces/FR-024-6.json` (exists, references non-existent test)

### Code Modules
- `docs/operations/journeys/FR-024-1.md` — exists, has YAML frontmatter (`fr_id`, `spec_slug`, `spec_anchor`, `status`, `captured_at`). 25 lines.
- `docs/operations/journeys/FR-024-2.md` — exists, same frontmatter structure.
- `docs/operations/journeys/FR-024-3.md` — exists, same frontmatter structure.
- `docs/operations/journeys/FR-024-4.md` — exists, same frontmatter structure.
- `docs/operations/journeys/FR-024-5.md` — exists, same frontmatter structure.
- `docs/operations/journeys/FR-024-6.md` — exists, same frontmatter structure.
- `docs/operations/journeys/FR-024-7.md` — exists, same frontmatter structure.
- `docs/operations/journeys/FR-024-8.md` — exists, same frontmatter structure.
- `crates/agileplus-trace-validator/src/lib.rs:118-136` — `validate_trace_paths()` checks that `journeys` paths exist on disk. This validates the file existence, but does not parse frontmatter.

### Tests
- `trace.json` references `tooling/trace-validator/tests/journey.rs::test_journey_stub_has_frontmatter` — file does not exist.
- No test in the repo verifies journey stub frontmatter, file existence, or content.
- The `cli.rs` fixture creates `docs/operations/journeys/FR-1.md` (line 39), but the test only checks that the trace validator accepts the path, not that the journey stub is valid.

### Gaps
- No automated test verifies journey stub existence or frontmatter.
- All 8 stubs are present but marked as "stub" in their body.

**Rating:** PARTIAL (8 journey stubs exist with correct frontmatter, no automated test coverage).

---

## FR-024-7 — `--check-anchors` mode

**Spec:** `kitty-specs/eco-024-traceability/spec.md:54-56`  
**Trace:** `traces/FR-024-7.json` (exists, references non-existent code and test)

### Code Modules
- `crates/agileplus-trace-validator/src/main.rs` — No `--check-anchors` subcommand.
- `crates/agileplus-trace-validator/src/lib.rs` — No anchor resolution logic.
- `traces/SCHEMA.md:25` — Mentions "the validator's `--check-anchors` mode enforces this", but the mode is not implemented.

### Tests
- `trace.json` references `tooling/trace-validator/tests/anchors.rs::test_dangling_anchor_fails` — file does not exist.
- No test in the repo references anchor checking.

### Gaps
- Feature is entirely unimplemented.
- No code module, no CLI flag, no test.

**Rating:** NONE (no code, no tests).

---

## FR-024-8 — `SCHEMA.md` versioning

**Spec:** `kitty-specs/eco-024-traceability/spec.md:57-58`  
**Trace:** `traces/FR-024-8.json` (exists, references non-existent test)

### Code Modules
- `traces/SCHEMA.md:1-40` — Exists, declares v1, documents field rules, validator behavior, and versioning policy.
- `crates/agileplus-trace-validator/src/lib.rs:103` — `read_trace()` hardcodes `schema_version` field check via `value.get(field)` but does **not** read `SCHEMA.md` to validate version. The code simply checks that `schema_version` is a string field present in the JSON.
- `traces/FR-024-1.json` through `traces/FR-024-8.json` — All contain `"schema_version": "1"`.

### Tests
- `trace.json` references `tooling/trace-validator/tests/schema.rs::test_schema_md_matches_shape` — file does not exist.
- No test in the repo verifies that `SCHEMA.md` version matches the validator's hardcoded checks.
- `crates/agileplus-trace-validator/tests/edge_cases.rs:199-214` — `validate_malformed_json_array_payload_fails` tests shape validation, but does not test schema versioning.

### Gaps
- Validator does not read `SCHEMA.md` at runtime.
- No test ensures `SCHEMA.md` and code are in sync.
- Schema version is hardcoded in the code, not dynamically loaded.

**Rating:** PARTIAL (`SCHEMA.md` exists, validator checks for `schema_version` field, but no dynamic versioning and no tests).

---

## Cross-FR Artifact Counts

| Artifact | Count | Details |
|----------|-------|---------|
| Trace JSON files | 8 | `traces/FR-024-{1..8}.json` |
| Journey stubs | 8 | `docs/operations/journeys/FR-024-{1..8}.md` |
| Source files in validator crate | 5 | `src/lib.rs`, `src/main.rs`, `src/graph.rs`, `src/loaders.rs`, `src/rules.rs` |
| Test files in validator crate | 2 | `tests/cli.rs`, `tests/edge_cases.rs` |
| Test functions in validator crate | 10 | 2 in `cli.rs`, 8 in `edge_cases.rs` |
| Dangling paths in trace.json | 8 | Every trace.json references `tooling/trace-validator/...` which does not exist |
| Missing workflow files | 1 | `.github/workflows/agileplus-traceability.yml` |
| Missing test files | 6 | `spec.rs`, `ci.rs`, `matrix.rs`, `journey.rs`, `anchors.rs`, `schema.rs` |

---

## Dangling Path Analysis

All 8 `trace.json` files contain paths under `tooling/trace-validator/...`. The actual crate lives at `crates/agileplus-trace-validator/`. The `tooling/` directory only contains `governance_index.py`.

| FR | Dangling `code_modules` path | Dangling `tests` path |
|----|------------------------------|----------------------|
| FR-024-1 | `tooling/trace-validator/src/main.rs` | `tooling/trace-validator/tests/spec.rs::test_fr1_trace_required` |
| FR-024-2 | `tooling/trace-validator/src/schema.rs` | `tooling/trace-validator/tests/spec.rs::test_fr2_schema_fields` |
| FR-024-3 | `tooling/trace-validator/src/main.rs`, `tooling/trace-validator/src/walk.rs` | `tooling/trace-validator/tests/cli.rs::test_validator_runs` |
| FR-024-4 | `.github/workflows/agileplus-traceability.yml` | `tooling/trace-validator/tests/ci.rs::test_ci_workflow_runs_validator` |
| FR-024-5 | `tooling/trace-validator/src/matrix.rs` | `tooling/trace-validator/tests/matrix.rs::test_matrix_renders_all_frs` |
| FR-024-6 | `tooling/trace-validator/src/journey.rs` | `tooling/trace-validator/tests/journey.rs::test_journey_stub_has_frontmatter` |
| FR-024-7 | `tooling/trace-validator/src/anchors.rs` | `tooling/trace-validator/tests/anchors.rs::test_dangling_anchor_fails` |
| FR-024-8 | `tooling/trace-validator/src/schema.rs` | `tooling/trace-validator/tests/schema.rs::test_schema_md_matches_shape` |

**Total dangling paths:** 8 code_modules + 8 tests = 16 dangling references.

---

## Source File Inventory (validator crate)

| File | Lines | FR-024 Relevance |
|------|-------|------------------|
| `crates/agileplus-trace-validator/src/lib.rs` | 159 | FR-024-1 (138-158), FR-024-2 (97-116), FR-024-8 (103) |
| `crates/agileplus-trace-validator/src/main.rs` | 67 | FR-024-3 (1-67), FR-024-5 (36-47) |
| `crates/agileplus-trace-validator/src/graph.rs` | 82 | FR-024-5 (potential, unused) |
| `crates/agileplus-trace-validator/src/loaders.rs` | 150 | FR-024-3 (graph loader, not directly trace) |
| `crates/agileplus-trace-validator/src/rules.rs` | 98 | FR-024-3 (graph validation rules, not directly trace) |
| `crates/agileplus-trace-validator/tests/cli.rs` | 60 | FR-024-1, FR-024-2, FR-024-3 (2 tests) |
| `crates/agileplus-trace-validator/tests/edge_cases.rs` | 279 | FR-024-1, FR-024-2, FR-024-3 (8 tests) |

---

*End of audit.*
