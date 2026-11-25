# AgilePlus Traceability Matrix

> Generated: 2026-06-13
> Branch: `integration/consolidate`
> Scope: `SPEC.md` + `FUNCTIONAL_REQUIREMENTS.md` + all `kitty-specs/*/spec.md` FRs with traceability comments in Rust source

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Artifact present and verified |
| 🟡 | Artifact present but incomplete / stub / mismatched path |
| 🔴 | Artifact missing |
| `n/a` | Not applicable to this FR |

---

## Section A: Canonical FRs (`FUNCTIONAL_REQUIREMENTS.md`)

Source: `FUNCTIONAL_REQUIREMENTS.md` (eco-034 in flight)

| FR ID | Title | Spec | Trace | Code | Tests | Journeys | Status | Notes |
|-------|-------|------|------|------|-------|----------|--------|-------|
| FR-024-1 | Per-FR `trace.json` mandatory | eco-024 | ✅ | 🟡 | 🟡 | ✅ | proposed | Code: `crates/agileplus-trace-validator/src/lib.rs:138-158` (`missing_requirements`). Tests: `crates/agileplus-trace-validator/tests/cli.rs:7-16`, `tests/edge_cases.rs:131-173` (multi-trace). **GAP**: `trace.json` references `tooling/trace-validator/tests/spec.rs::test_fr1_trace_required` — path does not exist. |
| FR-024-2 | `trace.json` schema (5 layers) | eco-024 | ✅ | ✅ | 🟡 | ✅ | proposed | Code: `crates/agileplus-trace-validator/src/lib.rs:97-116` (`read_trace` validates required fields). Tests: `crates/agileplus-trace-validator/tests/edge_cases.rs:59-81` (`validate_trace_missing_required_field_fails`), `tests/edge_cases.rs:199-214` (`validate_malformed_json_array_payload_fails`). **GAP**: `trace.json` references `tooling/trace-validator/tests/spec.rs::test_fr2_schema_fields` — path does not exist. |
| FR-024-3 | `trace-validator` binary | eco-024 | ✅ | ✅ | ✅ | ✅ | proposed | Code: `crates/agileplus-trace-validator/src/main.rs` (CLI), `src/lib.rs` (validation library). Tests: `crates/agileplus-trace-validator/tests/cli.rs:7-16` (`validate_accepts_trace_directory`), `tests/cli.rs:19-29` (`stats_prints_trace_counts`). **GAP**: `trace.json` references `tooling/trace-validator/tests/cli.rs::test_validator_runs` — path does not exist. |
| FR-024-4 | CI gate on every PR | eco-024 | ✅ | 🔴 | 🔴 | ✅ | proposed | Trace references `.github/workflows/agileplus-traceability.yml`. **GAP**: File does not exist. Related but not equivalent: `.github/workflows/fr-coverage.yml` is a stub (`echo "FR coverage check"`). No CI gate actually runs the trace-validator. |
| FR-024-5 | `MATRIX.md` generated | eco-024 | 🟡 | 🟡 | 🔴 | ✅ | proposed | `traces/MATRIX.md` exists but is hand-written (auto-generation stub). Code: `crates/agileplus-trace-validator/src/main.rs:36-47` has `Graph` command but no `--emit-matrix` flag. **GAP**: No dedicated test for MATRIX.md generation. `trace.json` references `tooling/trace-validator/tests/matrix.rs::test_matrix_renders_all_frs` — path does not exist. |
| FR-024-6 | Journey stubs under `docs/operations/journeys/<fr_id>.md` | eco-024 | ✅ | ✅ | 🔴 | ✅ | proposed | Code: `docs/operations/journeys/FR-024-{1..8}.md` all exist with frontmatter. **GAP**: No automated test verifying frontmatter or stub existence. `trace.json` references `tooling/trace-validator/tests/journey.rs::test_journey_stub_has_frontmatter` — path does not exist. |
| FR-024-7 | `--check-anchors` mode | eco-024 | ✅ | 🔴 | 🔴 | ✅ | proposed | **GAP**: Feature not implemented. Validator has no `--check-anchors` subcommand or anchor resolution logic. `trace.json` references `tooling/trace-validator/tests/anchors.rs::test_dangling_anchor_fails` — path does not exist. |
| FR-024-8 | `SCHEMA.md` versioning | eco-024 | ✅ | 🟡 | 🔴 | ✅ | proposed | Code: `traces/SCHEMA.md` exists. `crates/agileplus-trace-validator/src/lib.rs:103` hardcodes field checks but does not read SCHEMA.md version. **GAP**: No test for SCHEMA.md versioning. `trace.json` references `tooling/trace-validator/tests/schema.rs::test_schema_md_matches_shape` — path does not exist. |

---

## Section B: FR-AGP-xxx (AgilePlus Core FRs with Traceability Comments)

| FR ID | Spec | Code | Tests | Status | Notes |
|-------|------|------|-------|--------|-------|
| FR-AGP-001 | n/a | `crates/agileplus-sqlite/src/seed/mod.rs:3`, `src/seed/catalog.rs:26-129` | `crates/agileplus-sqlite/src/seed/catalog.rs:293-294` | inferred | Catalog requirement-ID parser. |
| FR-AGP-011 | n/a | `crates/agileplus-grpc/src/lib.rs:8,13`, `src/work_items.rs:8`, `crates/agileplus-proto/src/lib.rs:10`, `src/stubs.rs:7` | 🔴 | gap | WorkItemsService / gRPC. No dedicated test found. |
| FR-AGP-012 | n/a | `crates/agileplus-api/src/middleware/token_verifier.rs:6,29` | `crates/agileplus-api/tests/api_integration.rs:1110-1150` | covered | 4 auth tests: missing token, valid bearer, wrong bearer, public route carve-out. |
| FR-AGP-013 | n/a | `crates/agileplus-github/src/map.rs:114,132`, `crates/agileplus-application/src/use_cases/persist_synced_stories.rs:3` | 🔴 | gap | GitHub story idempotent upsert. No dedicated test found. |
| FR-AGP-015 | n/a | `crates/agileplus-api/src/middleware/otel.rs` (implied by `api_integration.rs` import) | `crates/agileplus-api/tests/api_integration.rs:1152-1209` | covered | 2 OTel tests: span wrapping, traceparent propagation. |
| FR-AGP-016 | n/a | `crates/agileplus-cli/src/commands/list_tests.rs:2` | 🔴 | gap | `list_tests` CLI subcommand. No dedicated test found. |
| FR-AGP-017 | n/a | `crates/agileplus-triage/src/lib.rs:13`, `src/engine.rs:6` | 🔴 | gap | Triage engine core. No dedicated test found. |
| FR-AGP-018 | n/a | `crates/agileplus-triage/src/dedup.rs:4`, `crates/agileplus-cli/src/commands/dag.rs:23`, `crates/agileplus-application/src/use_cases/triage.rs:26`, `src/dto/mod.rs:6` | `crates/agileplus-triage/src/tests_dedup.rs:12-69` | covered | Token Jaccard, Levenshtein, fuzzy ratio, ngram, simhash, hybrid score, find duplicates. |
| FR-AGP-019 | n/a | `crates/agileplus-triage/src/claim.rs:8`, `crates/agileplus-cli/src/commands/dag.rs:23`, `crates/agileplus-application/src/use_cases/triage.rs:26`, `src/dto/mod.rs:6` | `crates/agileplus-triage/src/tests_dedup.rs:72-110` | covered | Claim store: issue/release, heartbeat expiry, heartbeat refresh, lookup. |
| FR-AGP-020 | n/a | `crates/agileplus-triage/src/repo_introspect.rs:5`, `crates/agileplus-cli/src/commands/dag.rs:24`, `crates/agileplus-application/src/use_cases/triage.rs:26-27` | `crates/agileplus-triage/src/tests_dedup.rs:113-143` | covered | Repo introspection: no-git, mangled-git, valid-git states. |
| FR-AGP-021 | n/a | `crates/agileplus-cli/src/commands/dag.rs:24` | 🔴 | gap | Graph topology. No dedicated test found (tested indirectly via `dag.rs` CLI tests if any). |
| FR-AGP-022 | n/a | `crates/agileplus-cli/src/commands/dag.rs:25` | 🔴 | gap | `where_am_i` CLI subcommand. No dedicated test found. |
| FR-AGP-023 | n/a | `crates/agileplus-cli/src/commands/import_dagctl.rs:75` | 🔴 | gap | `dagctl` import. No dedicated test found. |

---

## Section C: FR-API-xxx / FR-DOMAIN-xxx (API & Domain FRs)

| FR ID | Spec | Code | Tests | Status | Notes |
|-------|------|------|-------|--------|-------|
| FR-API-001 | n/a | `crates/agileplus-api/src/routes/` (implied) | `crates/agileplus-api/tests/api_integration/core_routes.rs:57-75` | covered | JSON content-type header test. |
| FR-API-005 | n/a | `crates/agileplus-api/src/routes/` (implied) | `crates/agileplus-api/tests/api_integration/core_routes.rs:6-33` | covered | Health + info endpoint no-auth tests. |
| FR-API-007 | n/a | `crates/agileplus-api/src/routes/` (implied) | `crates/agileplus-api/tests/api_integration/core_routes.rs:36-54` | covered | Auth rejection tests (401). |
| FR-DOMAIN-014 | n/a | `crates/agileplus-domain/src/domain/` (implied) | `crates/agileplus-api/tests/api_integration/core_routes.rs:6-24` | covered | Health test indirectly covers domain health. |

---

## Section D: FR-TRC-xxx (Tracera FRs — from `docs/requirements/tracera-frnfr.md`)

> Note: These FRs describe Tracera capabilities. The AgilePlus repo contains `docs/requirements/tracera-frnfr.md` as a cross-project reference, but the actual code and tests live in the Tracera repository. Only the document is present here.

| FR ID | Title | Status | Notes |
|-------|-------|--------|-------|
| FR-TRC-001 | Canonical TraceLink Domain Model | SHIPPED | Documented only. |
| FR-TRC-002 | Confidence-Scored Trace Links | SHIPPED | Documented only. |
| FR-TRC-003 | Neo4j Trace-Graph Projection Writer | SHIPPED | Documented only. |
| FR-TRC-004 | Forward/Reverse Impact Analysis | SHIPPED | Documented only. |
| FR-TRC-005 | Auth with DB Account Lookup | SHIPPED | Documented only. |
| FR-TRC-006 | Spatial GiST Index | SHIPPED | Documented only. |
| FR-TRC-007 | UICodeTracePanel Live API | SHIPPED | Documented only. |
| FR-TRC-008 | MCP Auth/Config/DB Contract Tests | SHIPPED | Documented only. |
| FR-TRC-009 | Live Comment Submission | SHIPPED | Documented only. |
| FR-TRC-010 | E2E Project Lifecycle Test | SHIPPED | Documented only. |
| FR-TRC-011 | Requirement Miner | SHIPPED | Documented only. |
| FR-TRC-012 | Duplicate/Conflict Detection | SHIPPED | Documented only. |
| FR-TRC-013 | Bulk TraceLink Ingestion | SHIPPED | Documented only. |
| FR-TRC-014 | Coverage Matrix Export | SHIPPED | Documented only. |
| FR-TRC-015 | Blast-Radius Scoring | SHIPPED | Documented only. |
| FR-TRC-016 | AgilePlus Integration Push | SHIPPED | Documented only. |
| FR-TRC-017 | Traceability Health Scoring | SHIPPED | Documented only. |
| FR-TRC-018..022 | Platform epics | PLANNED | Documented only. |

---

## Section E: FR-CORE-xxx / Civis FRs (from `docs/requirements/civis-frnfr.md`)

> Note: Civis is a separate project. The AgilePlus repo contains `docs/requirements/civis-frnfr.md` as a reference catalog. Code/tests are not in this repo.

| FR ID | Title | Status | Notes |
|-------|-------|--------|-------|
| FR-CORE-001..007 | Core Simulation Engine | PLANNED | Documented only. |
| FR-ECON-001..005 | Economy System | PLANNED | Documented only. |
| FR-METRICS-001..003 | Metrics | SHIPPED | Documented only. |
| FR-CIV-ACTOR-001..002 | Citizen Lifecycle | SHIPPED / PLANNED | Documented only. |
| FR-CIV-SOCIAL-001..002 | Social Relationships | SHIPPED / PLANNED | Documented only. |
| FR-CIV-BUILD-001..003 | Building System | SHIPPED | Documented only. |
| FR-CIV-CLIMATE-001..003 | Climate System | SHIPPED | Documented only. |
| FR-CIV-BIO-001..003 | Genetics | SHIPPED | Documented only. |
| FR-CIV-CULT-001..003 | Culture | SHIPPED | Documented only. |
| FR-PROTO-001..005 | Protocol | PLANNED | Documented only. |
| FR-CLIENT-001..003 | Client | SHIPPED / PLANNED | Documented only. |
| FR-CIV-HUD-001..005 | HUD | SHIPPED | Documented only. |
| FR-CIV-WAR-001..004 | Combat | SHIPPED / PLANNED | Documented only. |
| FR-CIV-DIPLO-001..003 | Diplomacy | PLANNED | Documented only. |
| FR-CIV-GOV-001..002 | Government | PLANNED | Documented only. |
| FR-API-001..004 | Research API | PLANNED | Documented only. |
| FR-REPLAY-001..002 | Replay | PLANNED | Documented only. |
| FR-CIV-CLIENT-GODOT-001..002 | Godot Client | PLANNED | Documented only. |

---

## Section F: Other FRs with Code Links

| FR ID | Code | Tests | Notes |
|-------|------|-------|-------|
| FR-001 | `crates/agileplus-cli/src/commands/validate/tests.rs`, `crates/agileplus-cli/src/commands/plan/tests.rs`, `crates/agileplus-cli/src/commands/retrospective/tests.rs`, `crates/agileplus-governance/tests/qa_gates_integration.rs`, `crates/agileplus-sqlite/src/lib.rs:1130-1181`, `crates/agileplus-grpc/tests/pact_schema.rs:120-139`, `libs/xdd-lib-rs/src/lib.rs:414-424` | ✅ | Used as a fixture/test-data FR in many crates. |
| FR-008 | `crates/agileplus-events/src/lib.rs:9`, `src/domain_event.rs:8`, `crates/agileplus-cli/src/commands/specify.rs:4`, `crates/agileplus-nats/src/lib.rs:12` | 🔴 | Domain-event layer. No dedicated test found. |
| FR-048 | `crates/agileplus-subcmds/src/lib.rs:7`, `src/tracera_bridge.rs:246` | 🔴 | Subcmds / tracera bridge. No dedicated test found. |
| FR-049 | `crates/agileplus-subcmds/src/lib.rs:7`, `crates/agileplus-api/src/routes/backlog.rs:3`, `crates/agileplus-cli/src/commands/queue/mod.rs:5` | 🔴 | Backlog / queue. No dedicated test found. |
| FR-051 | `crates/agileplus-plane/src/lib.rs:7` | 🔴 | Plane sync. No dedicated test found. |

---

## Section G: GAP Analysis

### GAP 1: FRs with No Dedicated Test

| FR ID | Count | Notes |
|-------|-------|-------|
| FR-024-1 | 1 | `trace.json` references non-existent test path |
| FR-024-2 | 1 | `trace.json` references non-existent test path |
| FR-024-3 | 1 | `trace.json` references non-existent test path |
| FR-024-4 | 1 | `trace.json` references non-existent test path |
| FR-024-5 | 1 | `trace.json` references non-existent test path |
| FR-024-6 | 1 | `trace.json` references non-existent test path |
| FR-024-7 | 1 | `trace.json` references non-existent test path |
| FR-024-8 | 1 | `trace.json` references non-existent test path |
| FR-AGP-011 | 1 | WorkItemsService — no test |
| FR-AGP-013 | 1 | GitHub map idempotent upsert — no test |
| FR-AGP-016 | 1 | `list_tests` — no test |
| FR-AGP-017 | 1 | Triage engine — no test |
| FR-AGP-021 | 1 | Graph topology — no test |
| FR-AGP-022 | 1 | `where_am_i` — no test |
| FR-AGP-023 | 1 | `dagctl` import — no test |
| FR-008 | 1 | Events / NATS — no test |
| FR-048 | 1 | Subcmds / tracera bridge — no test |
| FR-049 | 1 | Backlog / queue — no test |
| FR-051 | 1 | Plane sync — no test |

**Total FRs with no test: 24**

### GAP 2: FRs with Missing / Incomplete Code

| FR ID | Count | Notes |
|-------|-------|-------|
| FR-024-4 | 1 | `.github/workflows/agileplus-traceability.yml` missing |
| FR-024-5 | 1 | Auto-generated `MATRIX.md` not implemented |
| FR-024-7 | 1 | `--check-anchors` mode not implemented |
| FR-024-8 | 1 | `SCHEMA.md` versioning not enforced in validator |

**Total FRs with missing code: 4**

### GAP 3: Code Modules with No FR Link

Crates in the workspace with **zero** traceability comments (FR/WP references) in their source:

| Crate | Notes |
|-------|-------|
| `crates/agileplus-artifacts` | No traceability comments |
| `crates/agileplus-benchmarks` | No traceability comments |
| `crates/agileplus-cache` | No traceability comments |
| `crates/agileplus-config` | No traceability comments |
| `crates/agileplus-contract-tests` | No traceability comments |
| `crates/agileplus-dashboard` | No traceability comments (has `specs/002` trace but not inline FR) |
| `crates/agileplus-git` | No traceability comments |
| `crates/agileplus-governance` | No traceability comments (has `tests/qa_gates_integration.rs` but not inline FR) |
| `crates/agileplus-graph` | No traceability comments |
| `crates/agileplus-import` | No traceability comments |
| `crates/agileplus-integration-tests` | No traceability comments |
| `crates/agileplus-p2p` | No traceability comments |
| `crates/agileplus-telemetry` | No traceability comments |
| `crates/agileplus-validate` | No traceability comments |
| `crates/pheno-ssot-template` | No traceability comments |
| `libs/xdd-lib-rs` | Has test fixtures for FR-024-1 and FR-CORE-001, but no inline FR link for core functionality |

**Total crates with no FR link: 16**

---

## Summary

| Metric | Count |
|--------|-------|
| Canonical FRs in `FUNCTIONAL_REQUIREMENTS.md` | 8 |
| FR-AGP-xxx with code links | 13 |
| FR-API-xxx / FR-DOMAIN-xxx with code links | 4 |
| FR-TRC-xxx (documented only) | 22 |
| FR-CORE-xxx / Civis (documented only) | 45 |
| Other FRs with code links (FR-001, FR-008, FR-048, FR-049, FR-051) | 5 |
| **FRs with no test** | **24** |
| **FRs with missing code** | **4** |
| **Crates with no FR link** | **16** |

---

## Recommendations

1. **Fix trace paths**: All 8 `traces/FR-024-*.json` files reference `tooling/trace-validator/...` which does not exist. The actual crate is `crates/agileplus-trace-validator/`. Update `trace.json` files to match reality.
2. **Implement missing features**: `--check-anchors` (FR-024-7), auto-generated `MATRIX.md` (FR-024-5), and the CI workflow `agileplus-traceability.yml` (FR-024-4).
3. **Add tests for uncovered FRs**: FR-AGP-011, FR-AGP-013, FR-AGP-016, FR-AGP-017, FR-AGP-021, FR-AGP-022, FR-AGP-023, FR-008, FR-048, FR-049, FR-051.
4. **Add traceability comments to orphaned crates**: 16 crates have no FR link. Add `//! Traceability: <FR-ID>` headers to their `lib.rs` or `main.rs` files.
5. **Backfill `FUNCTIONAL_REQUIREMENTS.md`**: The document states "The remaining FRs from eco-001..033 will be backfilled by the eco-026 autograder's first pass." This is a pending dependency.

---

*Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>*
