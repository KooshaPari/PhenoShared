# A-10 Validation: Fix L0-L2 Violations from Scorecard

## Objective

Address 5 P0 blocking issues identified in `docs/audit/scorecard.json`
for `phenotype-infra`:

| Scorecard Pillar | Score | Description | What was done |
|---|---|---|---|
| L4 — test-coverage | 1/5 | No test files present | Created `tests/integration_test.rs` with cross-crate integration tests covering `nvms-ffi`, `pheno-compose-driver`, `pheno-config`, error types, and health check |
| L11 — error-handling | 1/5 | No consistent error type strategy | Created `crates/pheno-compose/src/errors.rs` with `thiserror`-based `Error` enum, `From` impls for `nvms_ffi::NvmsError`, and `Result<T>` alias |
| L15 — testing-strategy | 1/5 | No test directory at monorepo root | Created `tests/` directory with its own `Cargo.toml` (workspace member) and `tests/integration_test.rs` exercising all crates |
| L17 — monitoring | 1/5 | No monitoring setup | Created `crates/pheno-compose/src/health.rs` with `check()` → `HealthReport`, probes (init/version/platform), serde round-trip, and never-panics guarantee |
| L20 — community-health | 1/5 | No CONTRIBUTING.md, no issue templates | Ported `CONTRIBUTING.md` and `CODEOWNERS` from `nanovms` source repo, adapted for phenotype-infra (Rust workspace, updated paths, build/test commands, scopes) |

## Files Changed

```
 M .gitignore                              # Add tmp_* / tmp-* patterns
 A CODEOWNERS                              # Ported from nanovms, adapted for Rust workspace
 A CONTRIBUTING.md                         # Ported from nanovms, adapted for phenotype-infra
 M Cargo.lock                              # Updated with new dep versions
 M Cargo.toml                              # Added "tests" workspace member
 M crates/pheno-compose/Cargo.toml         # Added thiserror, serde deps; nvms-ffi made unconditional
 A crates/pheno-compose/src/errors.rs       # L11: error types (thiserror-based Error enum)
 A crates/pheno-compose/src/health.rs       # L17: health-check module with probes
 M crates/pheno-compose/src/lib.rs          # Register errors, health modules
 M crates/pheno-config/src/lib.rs           # Fix pre-existing compilation error (missing Format import)
 A tests/Cargo.toml                         # L4+L15: test workspace member manifest
 A tests/integration_test.rs                # L4+L15: cross-crate integration tests
```

## How to Validate

### Build (requires Rust 1.75+)

```bash
cargo check --workspace
```

Note: `nanovms-core` build may fail if Go 1.23+ is not installed; the
build script falls back automatically (warning only).

### Run tests

```bash
cargo test --workspace
```

Key test groups:

- **nvms-ffi tests** (embedded in `nvms-ffi/src/lib.rs`):
  - `exposes_version_and_platform`
  - `drives_instance_lifecycle`

- **pheno-compose-driver unit tests** (embedded in `pheno-compose/src/`):
  - `lib.rs`: `test_driver_initialization`, `test_create_wasm_instance`,
    `test_instance_lifecycle`
  - `config.rs`: `test_wasm_config`, `test_gvisor_config`, `test_firecracker_config`
  - `errors.rs`: `error_display_formatting`, `ffi_error_conversion`,
    `all_error_variants_are_debug_and_display`
  - `health.rs`: `health_check_never_panics`, `health_report_is_serializable`

- **Cross-crate integration tests** (`tests/integration_test.rs`):
  - `nvms_ffi_version_and_platform`
  - `nvms_ffi_instance_lifecycle`
  - `pheno_compose_driver_initialization`
  - `pheno_compose_driver_create_and_lifecycle`
  - `pheno_compose_driver_multiple_tiers`
  - `pheno_compose_driver_with_config`
  - `health_check_returns_report`
  - `health_report_serialization_roundtrip`
  - `error_type_conversion_from_ffi`
  - `error_type_display_formatting`
  - `pheno_config_defaults_are_sensible`

### Scorecard Re-assessment (future)

Run the scorecard workflow to confirm:

```yaml
# Expected improvements
L4-test-coverage:    1 → 3  (unit + integration tests present)
L11-error-handling:  1 → 3  (defined error type with thiserror)
L15-testing-strategy: 1 → 3 (cross-crate integration test suite)
L17-monitoring:      1 → 3  (health-check module with probes)
L20-community-health: 1 → 4  (CONTRIBUTING.md + CODEOWNERS ported)
```
