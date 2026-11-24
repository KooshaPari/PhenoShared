# AGENTS — `phenotype-config-loader`

## Scope

This crate contains **only** the small JSON/TOML file-loader primitives.
It is the entry-point of the Configra tier-2 library family; any new
loader primitive (YAML, HCL, INI, etc.) belongs here.

## Boundaries

- **In scope:** file IO + serde-deserialize wrappers; small error enum;
  pure data flow; no I/O outside the loader API.
- **Out of scope:** env-var cascade (`pheno-config` owns this), settings
  lifecycle (`settly`), schema validation (`config-schema`).

## Conventions

- Public API surface must remain minimal: at most one function per file
  format. Adding a new format = adding one function + one test.
- `ConfigLoadError` is the only error type returned to callers. Internal
  `std::io::Error` is wrapped via `#[from]`; parse errors are stringified
  into `ConfigLoadError::Parse`.
- No new dependencies without updating the workspace root and ADR.

## Adding a new file format

1. Add a function: `load_<format><T: DeserializeOwned>(&Path) -> Result<T, ConfigLoadError>`.
2. Add a unit test in the `mod tests` block at the bottom of `src/lib.rs`.
3. Update `README.md` "Quickstart" and `CHANGELOG.md`.
4. Run: `cargo test -p phenotype-config-loader` (must stay 100% green).
5. Run: `cargo clippy -p phenotype-config-loader --all-targets -- -D warnings`.

## Quality gates (ADR-040, tier-2 library)

- Coverage: ≥ 80% (current: 100% line, 100% branch on 3 unit tests).
- Lints: `cargo clippy --all-targets -- -D warnings` clean.
- Format: `cargo fmt --check` clean.
- Audit: `cargo audit` clean (thiserror / serde / serde_json / toml).

## Cross-references

- ADR-031 — Configra absorb
- ADR-022 — Config consolidation (two-crate canonical split)
- ADR-040 — Test coverage gates per tier
- ADR-023 — Agent-effort governance
