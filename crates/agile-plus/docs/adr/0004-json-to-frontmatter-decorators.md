# ADR-0004: JSON Metadata → YAML Frontmatter + Code Decorators

## Status

Accepted

## Context

`kitty-specs/*/meta.json` duplicated metadata already partially present in
`spec.md` frontmatter. `traces/FR-*.json` duplicated cross-layer coverage data
that belongs adjacent to journey narratives. Hand-maintained JSON drifted from
specs and journeys.

## Decision

1. **Spec metadata**: Fold `meta.json` fields into `spec.md` YAML frontmatter.
   Archive original JSON under `docs/_archive/meta-json/`.
2. **Trace cross-refs**: Fold `traces/FR-*.json` fields into `docs/journeys/FR-*.md`
   frontmatter (`fr_id`, `spec_slug`, `spec_anchor`, `docs_pages`, `tests`,
   `code_modules`, `journeys`, `status`, `last_validated`). Archive JSON under
   `docs/_archive/traces-json/`.
3. **Code decorators** (planned derivation): Rust modules/tests annotate coverage
   with a proc-macro or attribute convention:

   ```rust
   #[trace_fr(spec = "eco-024-traceability", fr = "FR-024-1")]
   fn validate_trace_required() { /* ... */ }
   ```

   A build-step collector (`xtask` or `agileplus-trace-validator`) scans
   `#[trace_fr(...)]` annotations and emits the coverage matrix as
   **generated** JSON/Markdown under `target/traceability/` (not committed).
4. **Hand-maintained JSON is retired** for trace metadata; only machine-generated
   derived artifacts remain as JSON.

## Consequences

- Validators read frontmatter + static analysis instead of parallel JSON trees.
- Matrix regeneration becomes deterministic from code + docs sources.
- Migration script: `scripts/phase3-docs-consolidate.py`.
- Decorator proc-macro implementation is a follow-up task; ADR locks the convention.
