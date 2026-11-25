# AGENTS — `config-schema`

## Scope

This crate provides the **field-shape validator** primitive. It answers
"does this JSON config have the required fields and right types?" with
a builder API and zero schema-DSL.

## Boundaries

- **In scope:** `SchemaField`, `ConfigSchema`, `SchemaError`, and the
  `validate(&serde_json::Value)` entry-point.
- **Out of scope:** full JSON-schema (Draft 4/7/2020-12); nested schemas;
  `$ref` resolution; remote schemas; env-var cascade; file loading.

## Conventions

- Keep the public surface minimal — adding a new field type means adding
  a `SchemaField::new(...)` constructor only.
- The error type stays flat: `MissingField(String)` and `WrongType` with
  three named fields. No nested cause chains.
- Deps stay at the floor: `serde_json` + `thiserror`. Do not add
  `serde`, `serde_derive`, `toml`, or any I/O deps to this crate.

## Adding a new error variant

1. Add the variant to `SchemaError` in `src/lib.rs`.
2. Add the `Display` impl via `#[error("...")]`.
3. Add a unit test that triggers the variant.
4. Run: `cargo test -p config-schema`.
5. Update `CHANGELOG.md`.

## Quality gates (ADR-040, tier-2 library)

- Coverage: ≥ 80% (current: 100% on the validator path).
- Lints: `cargo clippy -p config-schema --all-targets -- -D warnings`.
- Format: `cargo fmt --check` clean.
- Audit: `cargo audit` clean.

## Cross-references

- ADR-031 — Configra absorb
- ADR-022 — Config consolidation (two-crate canonical split)
- ADR-040 — Test coverage gates per tier
- ADR-023 — Agent-effort governance
