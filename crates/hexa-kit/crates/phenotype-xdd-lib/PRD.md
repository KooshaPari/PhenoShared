# phenotype-xdd-lib — Product Requirements Document

## Product Vision

`phenotype-xdd-lib` is a Rust library providing cross-cutting xDD (extreme/cross-disciplinary Development) utilities — property-based testing strategies, contract verification for hexagonal ports, mutation coverage tracking, and executable specification parsing — so Phenotype Rust services share a consistent, methodology-driven quality assurance toolkit without reimplementing testing infrastructure.

---

## Epics

### E1: Property-Based Testing Strategies

**Goal**: Provide reusable proptest and quickcheck strategy definitions for common Phenotype domain types (UUIDs, email addresses, timestamps, identifiers) so property tests are written once and shared across crates.

**User Stories**:

- E1.1: As a Rust developer, I want a `valid_uuid(s: &str) -> Result<Uuid, UuidError>` validator strategy so property tests can generate and verify well-formed UUID strings without per-crate UUID logic.
  - AC: `valid_uuid` accepts all UUID v4 format strings and rejects malformed strings.
  - AC: Exported from `phenotype_xdd_lib::property::strategies`.
  - Source: `src/property/strategies.rs`

- E1.2: As a Rust developer, I want proptest strategy combinators for generating bounded strings, numeric ranges, and valid identifier patterns so property tests cover realistic input domains.
  - AC: Strategies are composable with proptest's `prop_compose!` macro.
  - AC: All strategies are exported from `src/property/strategies.rs`.
  - Source: `src/property/strategies.rs`

- E1.3: As a Rust developer, I want quickcheck `Arbitrary` implementations for common domain types so tests using the quickcheck framework can generate valid instances automatically.
  - AC: Quickcheck generators implemented in `src/property/mod.rs`.
  - Source: `src/property/mod.rs`, `Cargo.toml` — `quickcheck = "1.0"`

- E1.4: As a maintainer, I want the property module to have zero dependencies on std I/O or async runtimes so strategies can be used in `#[no_std]` compatible crates.
  - AC: `src/property/` imports from `proptest`, `quickcheck`, and `std::collections` only.
  - Source: `src/property/`

---

### E2: Contract Testing Framework for Hexagonal Ports

**Goal**: Enable port/adapter contract verification — given an interface (port) and an implementation (adapter), assert that the adapter satisfies all behavioral contracts specified by the port.

**User Stories**:

- E2.1: As an architect, I want a `Contract` trait with a `name()` method so contract test suites are self-describing and identifiable in test output.
  - AC: `pub trait Contract { fn name() -> &'static str where Self: Sized; }` exported from `src/contract/mod.rs`.
  - Source: `src/contract/mod.rs:Contract`

- E2.2: As a developer, I want a `ContractVerifier` struct that accumulates contract verification results and reports pass/fail counts so test output shows which adapters satisfy which contracts.
  - AC: `ContractVerifier::new()` creates an empty verifier.
  - AC: `verifier.verify::<AdapterType>()` runs all contract checks against `AdapterType`.
  - AC: `verifier.report()` returns a structured `ContractReport` with pass/fail/total counts.
  - Source: `src/contract/mod.rs:ContractVerifier`

- E2.3: As a developer, I want contract verification to return a typed `XddResult<ContractReport>` rather than panicking so contract failures are catchable in CI reporting loops.
  - AC: `ContractVerifier::verify` returns `XddResult<()>` not `()`.
  - AC: Failures accumulate rather than short-circuit so all violations are visible in one run.
  - Source: `src/contract/mod.rs`, `src/domain/mod.rs:XddResult`

- E2.4: As an architect, I want a standard contract test pattern that verifies bidirectional port/adapter compliance (port → adapter AND adapter → port) so adapters cannot partially implement ports.
  - AC: Contract library provides a macro or trait that enforces complete `impl Trait` for all methods.
  - Source: `src/contract/mod.rs`

---

### E3: Mutation Coverage Tracking

**Goal**: Provide a `MutationTracker` that records line/branch execution and mutation kill/survive status, computing a mutation score, so teams can measure test quality beyond line coverage.

**User Stories**:

- E3.1: As a test engineer, I want `MutationTracker::record_execution(file: &str, line: usize)` to record which lines were executed so a coverage map is built during test runs.
  - AC: `MutationTracker` stores a `HashMap<String, FileCoverage>` of per-file execution data.
  - AC: `record_execution` is goroutine-safe (uses `Mutex` or `RwLock` internally).
  - Source: `src/mutation/mod.rs:MutationTracker`

- E3.2: As a test engineer, I want `MutationTracker::mutation_score() -> f64` to return the ratio of killed mutations to total mutations so CI can enforce a minimum mutation score threshold.
  - AC: Score is `killed_mutations / total_mutations` as `f64`; returns 0.0 when `total_mutations == 0`.
  - Source: `src/mutation/mod.rs:MutationTracker.mutation_score()`

- E3.3: As a test engineer, I want `MutationStatus` variants (`Killed`, `Survived`, `Equivalent`) with serde serialization so mutation reports can be persisted as JSON for trend analysis.
  - AC: `MutationStatus` derives `Serialize`, `Deserialize` with `snake_case` rename.
  - Source: `src/mutation/mod.rs:MutationStatus`

- E3.4: As a test engineer, I want `MutationKind` variants covering the standard mutation operators (arithmetic, logical, relational, value-based) so mutation categories are trackable in reports.
  - AC: `MutationKind` enum exported from `src/mutation/mod.rs`.
  - Source: `src/mutation/mod.rs:MutationKind`

---

### E4: Executable Specification Parsing (SpecDD)

**Goal**: Parse YAML-format executable specifications into a typed `Spec` structure so specification-driven tests can validate that features trace to documented requirements.

**User Stories**:

- E4.1: As a developer, I want `SpecParser::parse_yaml(yaml_str: &str) -> XddResult<Spec>` so spec files are loaded from YAML without manual deserialization.
  - AC: Parser uses `serde_yaml` (via `serde` feature) to deserialize into `Spec`.
  - AC: Parse errors include line numbers via serde_yaml error context.
  - Source: `src/spec/mod.rs:SpecParser`

- E4.2: As a developer, I want a `Spec` struct with `SpecMetadata` (`name`, `version`, `description`) and `Vec<Feature>` and `Vec<Requirement>` collections so the full spec structure is represented in a single typed value.
  - AC: All struct fields derive `Serialize`, `Deserialize`, `Debug`, `Clone`.
  - AC: `features` and `requirements` default to empty vecs when absent from YAML.
  - Source: `src/spec/mod.rs:Spec`, `SpecMetadata`, `Feature`, `Requirement`

- E4.3: As a developer, I want `SpecValidator::validate(spec: &Spec) -> XddResult<()>` so spec files with missing required fields fail loudly before tests run.
  - AC: Validation checks that `spec.name` and `spec.version` are non-empty strings.
  - AC: Validation checks that each feature `id` is unique and non-empty.
  - Source: `src/spec/mod.rs:SpecValidator`

- E4.4: As a developer, I want `Feature` to have a BDD scenario structure (`given`, `when`, `then` optional fields) so spec files double as BDD documentation.
  - AC: `Feature.scenario` is `Option<Scenario>` with optional `given`, `when`, `then` string fields.
  - Source: `src/spec/mod.rs:Feature`

---

### E5: Domain Error Types and Result Aliases

**Goal**: Define typed error and result types that are shared across all xDD modules so error handling is consistent and errors are categorized by xDD methodology.

**User Stories**:

- E5.1: As a library user, I want an `XddError` enum with variants covering property (`PropertyTestFailed`), contract (`ContractViolated`), mutation (`MutationTrackerError`), and spec (`SpecParseError`, `SpecValidationError`) failures so errors are categorized by methodology.
  - AC: `XddError` derives `thiserror::Error` and `Debug`.
  - AC: Each variant carries a descriptive `String` message.
  - Source: `src/domain/mod.rs:XddError`

- E5.2: As a library user, I want `type XddResult<T> = Result<T, XddError>` exported from the root crate so all module return types use a consistent alias.
  - AC: `XddResult` is re-exported from `src/lib.rs`.
  - Source: `src/lib.rs:XddResult`

- E5.3: As a library user, I want all public items re-exported from `src/lib.rs` (domain errors, strategies, contract verifier) so import paths are `phenotype_xdd_lib::strategies::*` not `phenotype_xdd_lib::property::strategies::*`.
  - AC: `pub use domain::{XddError, XddResult}` and `pub use property::strategies` in `src/lib.rs`.
  - Source: `src/lib.rs`

---

## Non-Functional Requirements

| Attribute | Requirement |
|-----------|-------------|
| Rust edition | 2021 |
| MSRV | Rust stable (no nightly features) |
| Dependencies | proptest 1.4, quickcheck 1.0, serde (derive), tokio (sync only for async-trait) |
| No-std compat | Property strategies module must be usable in `#[no_std]` contexts |
| Serialization | All public data types derive `serde::Serialize` and `serde::Deserialize` |

---

## Acceptance Criteria Summary

| Epic | Criterion |
|------|-----------|
| E1 | `valid_uuid("550e8400-e29b-41d4-a716-446655440000").is_ok()` |
| E2 | `ContractVerifier::verify` reports all violations without panicking |
| E3 | `mutation_score()` returns 0.0 for empty tracker; correct ratio for non-empty |
| E4 | `SpecParser::parse_yaml` round-trips to JSON via serde without data loss |
| E5 | All modules importable via `use phenotype_xdd_lib::*` |
