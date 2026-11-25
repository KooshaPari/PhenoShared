# FR-IMPORT-001 — AgilePlus Import Adapter Boundary

> Spec anchor: `specs/011-agileplus-import/`
> Status: PROPOSED → accepted on `cargo test -p agileplus-import` pass
> Crate: `agileplus-import`

## Description

The `agileplus-import` adapter ports external PM data (Jira, Linear, Trello,
CSV) into AgilePlus domain entities. The `Importer` port accepts a source
manifest, streams entities through the application port layer, and emits
typed `ImportEvent`s on the events bus. Idempotency is enforced via a
content-addressed dedupe key derived from source IDs plus schema version.

## Acceptance Criteria

| AC  | Criterion |
|-----|-----------|
| AC1 | `Importer` trait exposes `import(manifest) -> Result<ImportSummary>` returning counts, skipped, failed. |
| AC2 | Imported entities carry dedupe keys `{source, external_id, schema_version}`. |
| AC3 | Re-running an import with identical source IDs produces zero new rows. |
| AC4 | Failures are surfaced as `ImportEvent::Failed` and never silently dropped. |
| AC5 | At least one adapter (CSV) is wired with a passing integration test. |
| AC6 | `ImportSummary` shape: `{created, updated, skipped, failed, duration_ms}`. |
| AC7 | No adapter reads from a network or filesystem without going through the port. |
| AC8 | `import_integration.rs` proves ACs above with at least one assertion per AC. |

## Traceability

- Spec: `specs/011-agileplus-import/`
- Code: `crates/agileplus-import/src/`
- BDD: `specs/011-agileplus-import/bdd/`
- Tests: `crates/agileplus-import/tests/import_integration.rs`
- Journey: `docs/journeys/import-flow.md`
