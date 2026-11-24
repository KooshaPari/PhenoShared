# AP_SPEC_GAPS — Spec-to-Implementation Gap Audit

Generated: 2026-06-14
Scope: SPEC.md + FUNCTIONAL_REQUIREMENTS.md → crates/*

## FR/NFR IDs Extracted from SPEC.md

| ID | Title | Hits in crates/* |
|----|-------|------------------|
| *(none)* | — | — |

SPEC.md (`SPEC.md:1-46`) contains **zero** explicit FR or NFR identifiers.

## FR/NFR IDs Extracted from FUNCTIONAL_REQUIREMENTS.md

| ID | Title | Status | Hits in crates/* |
|----|-------|--------|------------------|
| FR-024-1 | Per-FR `trace.json` mandatory | proposed | **0** |
| FR-024-2 | `trace.json` schema (5 layers) | proposed | **0** |
| FR-024-3 | `trace-validator` binary | proposed | **0** |
| FR-024-4 | CI gate on every PR | proposed | **0** |
| FR-024-5 | `MATRIX.md` generated | proposed | **0** |
| FR-024-6 | Journey stubs under `docs/operations/journeys/<fr_id>.md` | proposed | **0** |
| FR-024-7 | `--check-anchors` mode | proposed | **0** |
| FR-024-8 | `SCHEMA.md` versioning | proposed | **0** |

Source: `FUNCTIONAL_REQUIREMENTS.md:12-19`

## Gaps (Zero Implementation References in crates/*)

All **8 FRs** from FUNCTIONAL_REQUIREMENTS.md have **zero** grep hits anywhere under `crates/*`:

- `FR-024-1` — no references in crates
- `FR-024-2` — no references in crates
- `FR-024-3` — no references in crates
- `FR-024-4` — no references in crates
- `FR-024-5` — no references in crates
- `FR-024-6` — no references in crates
- `FR-024-7` — no references in crates
- `FR-024-8` — no references in crates

## Where These IDs *Do* Appear (Outside crates/*)

| ID | Non-crate References |
|----|----------------------|
| FR-024-1 | `traces/SCHEMA.md:8`, `traces/MATRIX.md:14`, `docs/TRACEABILITY_MATRIX.md:24`, `docs/TRACEABILITY_MATRIX.md:138` |
| FR-024-2 | `traces/MATRIX.md:15`, `docs/TRACEABILITY_MATRIX.md:25`, `docs/TRACEABILITY_MATRIX.md:139` |
| FR-024-3 | `traces/MATRIX.md:16`, `docs/TRACEABILITY_MATRIX.md:26`, `docs/TRACEABILITY_MATRIX.md:140` |
| FR-024-4 | `traces/MATRIX.md:17`, `docs/TRACEABILITY_MATRIX.md:27`, `docs/TRACEABILITY_MATRIX.md:141` |
| FR-024-5 | `traces/MATRIX.md:18`, `docs/TRACEABILITY_MATRIX.md:28`, `docs/TRACEABILITY_MATRIX.md:142` |
| FR-024-6 | `traces/MATRIX.md:19`, `docs/TRACEABILITY_MATRIX.md:29`, `docs/TRACEABILITY_MATRIX.md:143` |
| FR-024-7 | `traces/MATRIX.md:20`, `docs/TRACEABILITY_MATRIX.md:30`, `docs/TRACEABILITY_MATRIX.md:144` |
| FR-024-8 | `traces/MATRIX.md:21`, `docs/TRACEABILITY_MATRIX.md:31`, `docs/TRACEABILITY_MATRIX.md:145` |

## Cross-Reference: Other FRs/NFRs Found in crates/*

The following FR/NFR IDs **are** referenced inside `crates/*` but were **not** listed in SPEC.md or FUNCTIONAL_REQUIREMENTS.md. They are included here for completeness:

| ID | crates/* Reference(s) |
|----|-----------------------|
| FR-001 | `agileplus-cli/src/commands/validate/tests.rs:21`, `agileplus-cli/src/commands/validate/tests.rs:38`, `agileplus-cli/src/commands/validate/tests.rs:50`, `agileplus-cli/src/commands/validate/tests.rs:60`, `agileplus-cli/src/commands/validate/tests.rs:67`, `agileplus-cli/src/commands/validate/tests.rs:98`, `agileplus-cli/src/commands/validate/tests.rs:114`, `agileplus-cli/src/commands/retrospective/tests.rs:22`, `agileplus-cli/src/commands/specify.rs:4`, `agileplus-cli/src/commands/pr_builder.rs:156`, `agileplus-cli/src/commands/pr_builder.rs:184`, `agileplus-cli/src/commands/pr_builder.rs:197`, `agileplus-cli/src/commands/pr_builder.rs:200`, `agileplus-cli/src/commands/plan.rs:503`, `agileplus-cli/src/commands/plan.rs:506`, `agileplus-cli/src/commands/plan.rs:546`, `agileplus-cli/src/commands/plan/tests.rs:6`, `agileplus-cli/src/commands/plan/tests.rs:9`, `agileplus-cli/src/commands/plan/tests.rs:48`, `agileplus-cli/src/commands/governance.rs:147`, `agileplus-governance/tests/qa_gates_integration.rs:25`, `agileplus-governance/tests/qa_gates_integration.rs:42`, `agileplus-grpc/tests/pact_schema.rs:120`, `agileplus-grpc/tests/pact_schema.rs:139`, `agileplus-sqlite/src/lib.rs:1130`, `agileplus-sqlite/src/lib.rs:1141`, `agileplus-sqlite/src/lib.rs:1159`, `agileplus-sqlite/src/lib.rs:1168`, `agileplus-sqlite/src/lib.rs:1177`, `agileplus-sqlite/src/lib.rs:1181`, `agileplus-sqlite/src/lib/tests/feature_work_packages.rs:352`, `agileplus-sqlite/src/lib/tests/feature_work_packages.rs:363`, `agileplus-sqlite/src/lib/tests/feature_work_packages.rs:381`, `agileplus-sqlite/src/lib/tests/feature_work_packages.rs:390`, `agileplus-sqlite/src/lib/tests/feature_work_packages.rs:399`, `agileplus-sqlite/src/lib/tests/feature_work_packages.rs:401`, `libs/xdd-lib-rs/src/lib.rs:414-424` |
| FR-002 | `agileplus-cli/src/commands/research.rs:4`, `agileplus-cli/src/commands/pr_builder.rs:184`, `agileplus-cli/src/commands/pr_builder.rs:197`, `agileplus-cli/src/commands/plan.rs:503`, `agileplus-cli/src/commands/plan/tests.rs:6`, `agileplus-cli/src/commands/plan/tests.rs:9`, `agileplus-sqlite/src/lib.rs:1168`, `agileplus-sqlite/src/lib/tests/feature_work_packages.rs:390` |
| FR-004 | `agileplus-cli/src/commands/implement.rs:5` |
| FR-005 | `agileplus-cli/src/commands/validate.rs:5` |
| FR-006 | `agileplus-cli/src/commands/ship.rs:5` |
| FR-007 | `agileplus-cli/src/commands/retrospective.rs:6` |
| FR-008 | `agileplus-events/src/lib.rs:9`, `agileplus-events/src/domain_event.rs:8`, `agileplus-cli/src/commands/specify.rs:4`, `agileplus-nats/src/lib.rs:12` |
| FR-009 | `agileplus-cli/src/commands/governance.rs:5` |
| FR-010 | `agileplus-cli/src/commands/implement.rs:5` |
| FR-011 | `agileplus-cli/src/commands/implement.rs:5`, `agileplus-cli/src/commands/pr_builder.rs:5` |
| FR-012 | `agileplus-cli/src/commands/implement.rs:5`, `agileplus-cli/src/commands/review_loop.rs:5` |
| FR-017 | `agileplus-sqlite/src/rebuild.rs:1` |
| FR-018 | `agileplus-cli/src/commands/validate.rs:5` |
| FR-019 | `agileplus-cli/src/commands/validate.rs:5` |
| FR-038 | `agileplus-cli/src/commands/scope.rs:5`, `agileplus-cli/src/commands/plan.rs:6` |
| FR-039 | `agileplus-cli/src/commands/scheduler.rs:5`, `agileplus-cli/src/commands/plan.rs:6` |
| FR-042 | `agileplus-cli/src/commands/pr_builder.rs:197`, `agileplus-cli/src/commands/pr_builder.rs:201` |
| FR-048 | `agileplus-subcmds/src/lib.rs:7`, `agileplus-subcmds/src/tracera_bridge.rs:246` |
| FR-049 | `agileplus-subcmds/src/lib.rs:7`, `agileplus-api/src/routes/backlog.rs:3`, `agileplus-cli/src/commands/queue/mod.rs:5` |
| FR-051 | `agileplus-plane/src/lib.rs:7` |
| NFR-002 | `agileplus-governance/tests/qa_gates_integration.rs:25`, `agileplus-governance/tests/qa_gates_integration.rs:42` |

> Note: FR-001, FR-002, FR-003, FR-004, etc. are referenced as test data and traceability comments, not as live specs in FUNCTIONAL_REQUIREMENTS.md.

## Summary

| Metric | Count |
|--------|-------|
| FR IDs read from SPEC.md | 0 |
| NFR IDs read from SPEC.md | 0 |
| FR IDs read from FUNCTIONAL_REQUIREMENTS.md | 8 |
| NFR IDs read from FUNCTIONAL_REQUIREMENTS.md | 0 |
| FR IDs with **zero** hits in `crates/*` | **8** |
| NFR IDs with **zero** hits in `crates/*` | **0** |
| Coverage rate (FRs referenced in crates) | **0 / 8 = 0%** |
