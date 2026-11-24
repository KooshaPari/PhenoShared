# Trace Schema (v1)

Every `trace.json` file under `AgilePlus/traces/<fr_id>.json` MUST conform to:

```json
{
  "schema_version": "1",
  "fr_id": "FR-024-1",
  "spec_slug": "eco-024-traceability",
  "spec_anchor": "#fr-1",
  "docs_pages": ["AgilePlus/docs/traceability.md"],
  "tests": ["tooling/trace-validator/tests/spec.rs::test_fr1_trace_required"],
  "code_modules": ["tooling/trace-validator/src/main.rs"],
  "journeys": ["docs/operations/journeys/FR-024-1.md"],
  "status": "proposed",
  "last_validated": "2026-06-05T00:00:00Z"
}
```

## Field rules

- `schema_version` MUST be `"1"` for v1.
- `fr_id` MUST be `FR-<spec_number>-<n>` and unique across the registry.
- `spec_slug` MUST match an active `AgilePlus/kitty-specs/*/meta.json` slug.
- `spec_anchor` MUST be a heading anchor (`#fr-N` or similar) in the spec's `spec.md`; the validator's `--check-anchors` mode enforces this.
- `docs_pages`, `tests`, `code_modules`, `journeys` MUST each be a JSON array (empty allowed). Every path MUST be repo-relative POSIX (no leading `/`, no `~/`).
- `status` MUST be one of `proposed | accepted | mature | regressed | pending-review`.
- `last_validated` MUST be an ISO-8601 UTC timestamp.

## Validator behavior

- Missing field → fail with `error: missing field <name> in trace <fr_id>`.
- Malformed path (absolute, `~`, contains `..`) → fail with `error: malformed path <path> in trace <fr_id>`.
- Dangling reference (file does not exist) → fail with `error: dangling reference <path> in trace <fr_id>`.
- Anchor mismatch (in `--check-anchors` mode) → fail with `error: anchor <anchor> not found in <spec_slug>/spec.md`.

## Versioning

- Bump `schema_version` in `SCHEMA.md` and the validator when changing the shape.
- The first version is v1; future versions are additive and deprecated fields are kept with a warning for at least one minor release.
