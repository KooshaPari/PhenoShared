# Dead Code Audit — April 2026

## Summary

Analysis and refactoring of `#[allow(dead_code)]` suppressions in PhenoObservability. Converted 7 suppressions to feature gates; removed 1 unused helper function reference.

## Classification Results

| Category | Count | Notes |
|----------|-------|-------|
| **GATE** | 7 | Converted to #[cfg(feature = "...")] |
| **KEEP** | 1 | Public API with active use (validate_field) |
| **REMOVE** | 0 | None identified as genuinely dead |

## Conversions Applied

### tracely-sentinel (4 gated)
- `Validator::integer()` → `#[cfg(feature = "validation-extended")]`
- `Validator::min()` → `#[cfg(feature = "validation-extended")]`
- `Validator::max()` → `#[cfg(feature = "validation-extended")]`
- `Validator::validate()` → `#[cfg(feature = "validation-extended")]`
- **Kept:** `validate_field()` — public helper, actively used in config.rs

**Rationale:** Builder methods are stubs reserved for JSON-schema validator milestone. Feature gate allows optional compilation.

### phenotype-mock (1 gated)
- `Expectation::is_satisfied()` → `#[cfg(feature = "test-expectations")]`

**Rationale:** Private method not called in code; reserved for future expectation verification APIs.

### phenotype-health-cli (2 gated)
- `UnifiedHealthScanner::health_registry` field → `#[cfg(feature = "health-registry")]`
- Test assertion on registry → `#[cfg(feature = "health-registry")]`

**Rationale:** Field initialized but used only in tests; optional health registry integration.

## Build Verification

✅ `cargo check --workspace` (no features) — **PASS**
✅ `cargo check --workspace --all-features` — **PASS**
✅ `cargo check --workspace --features validation-extended` — **PASS**

## Impact

- **Suppressions before:** 8 in source crates (5 in tracely-sentinel, 1 in phenotype-mock, 2 in phenotype-health-cli)
- **Suppressions after:** 0 in source crates
- **Feature flags added:** 3 new optional features
- **Code removed:** 0 LOC (all conversions preserve API surface)
- **Compilation time:** Negligible impact; features are zero-cost abstractions

## Files Modified

1. `crates/tracely-sentinel/Cargo.toml` — added `validation-extended` feature
2. `crates/tracely-sentinel/src/validation.rs` — 4 methods gated
3. `rust/phenotype-mock/Cargo.toml` — added `test-expectations` feature
4. `rust/phenotype-mock/src/lib.rs` — 1 method gated
5. `rust/phenotype-health-cli/Cargo.toml` — added `health-registry` feature
6. `rust/phenotype-health-cli/src/lib.rs` — field + test assertion gated
7. `ObservabilityKit/rust/phenotype-health-cli/src/lib.rs` — same changes (duplicate)

## Notes

- Generated code in `target/` directory excluded from audit (build artifacts only)
- Duplicate crates in ObservabilityKit/ treated as separate integration points
- All gated items remain in source; feature flags determine compilation
