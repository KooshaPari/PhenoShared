# Functional Requirements — phenotype-xdd-lib

**Crate:** `phenotype-xdd-lib`
**Version:** 0.1.0
**Language:** Rust (2021 edition)
**Traces to:** PRD.md Epics E1–E5

---

## Category Index

| Category | Prefix | Scope |
|----------|--------|-------|
| Property Testing | FR-PROP | Strategy definitions, generators, proptest/quickcheck |
| Contract Testing | FR-CONT | Port/adapter contract verification |
| Mutation Tracking | FR-MUT | Coverage tracking, mutation scoring |
| Spec Parsing | FR-SPEC | YAML spec parsing, validation, BDD structure |
| Domain Types | FR-DOM | Error types, result aliases, public API |

---

## FR-PROP — Property-Based Testing

### FR-PROP-001
**SHALL** export a `valid_uuid(s: &str) -> Result<(), UuidError>` validator function from `phenotype_xdd_lib::property::strategies` that accepts valid UUID v4 strings and returns `Err` for malformed strings.
**Traces to**: E1.1
**Source**: `src/property/strategies.rs`

### FR-PROP-002
**SHALL** provide proptest strategy definitions for generating valid UUID strings, email-like strings, bounded alphanumeric strings, and positive non-zero integers.
**Traces to**: E1.2
**Source**: `src/property/strategies.rs`

### FR-PROP-003
**SHALL** expose all property strategies from the `strategies` module so callers can import them via `use phenotype_xdd_lib::strategies::*` without needing sub-module paths.
**Traces to**: E1.2
**Source**: `src/lib.rs:pub use property::strategies`

### FR-PROP-004
**SHALL** provide quickcheck `Arbitrary` implementations for common domain types so tests using the quickcheck framework generate valid instances automatically.
**Traces to**: E1.3
**Source**: `src/property/mod.rs`, `Cargo.toml` — `quickcheck = "1.0"`

### FR-PROP-005
**SHALL** compile all property strategies with `#[no_std]` compatibility — the `src/property/` module SHALL NOT import `std::io`, `tokio`, or any async runtime.
**Traces to**: E1.4
**Source**: `src/property/` import constraints

---

## FR-CONT — Contract Testing

### FR-CONT-001
**SHALL** define a `Contract` trait in `src/contract/mod.rs` with an associated function `fn name() -> &'static str where Self: Sized` so contract test suites are self-describing.
**Traces to**: E2.1
**Source**: `src/contract/mod.rs:Contract`

### FR-CONT-002
**SHALL** provide a `ContractVerifier` struct with a `new() -> ContractVerifier` constructor and a `verify::<A>() -> XddResult<()>` method that runs all contract assertions against adapter type `A`.
**Traces to**: E2.2
**Source**: `src/contract/mod.rs:ContractVerifier`

### FR-CONT-003
**SHALL** accumulate all contract violations in `ContractVerifier::verify` rather than short-circuiting on first failure so all violations appear in a single report.
**Traces to**: E2.3
**Source**: `src/contract/mod.rs`

### FR-CONT-004
**SHALL** return `XddResult<ContractReport>` from `ContractVerifier::report()` where `ContractReport` contains `passed: usize`, `failed: usize`, `total: usize`, and `violations: Vec<String>`.
**Traces to**: E2.2, E2.3
**Source**: `src/contract/mod.rs`

### FR-CONT-005
**SHALL** provide a compile-time `contract_test!` macro (or equivalent proc-macro) that generates a `#[test]` function verifying a named adapter against a named contract, so contract tests are registered as Rust test cases.
**Traces to**: E2.4
**Source**: `src/contract/mod.rs`

---

## FR-MUT — Mutation Coverage Tracking

### FR-MUT-001
**SHALL** provide a `MutationTracker` struct with `fn new() -> MutationTracker` that initializes an empty `HashMap<String, FileCoverage>` state.
**Traces to**: E3.1
**Source**: `src/mutation/mod.rs:MutationTracker`

### FR-MUT-002
**SHALL** implement `MutationTracker::record_execution(file: &str, line: usize)` that increments the execution count for the given file and line, creating the `FileCoverage` entry if absent.
**Traces to**: E3.1
**Source**: `src/mutation/mod.rs:MutationTracker.record_execution()`

### FR-MUT-003
**SHALL** implement `MutationTracker::mutation_score() -> f64` returning the ratio `killed_mutations / total_mutations` as a value in `[0.0, 1.0]`, returning `0.0` when `total_mutations == 0`.
**Traces to**: E3.2
**Source**: `src/mutation/mod.rs:MutationTracker.mutation_score()`

### FR-MUT-004
**SHALL** define a `MutationStatus` enum with variants `Killed`, `Survived`, and `Equivalent` that derives `serde::Serialize` and `serde::Deserialize` with `#[serde(rename_all = "snake_case")]`.
**Traces to**: E3.3
**Source**: `src/mutation/mod.rs:MutationStatus`

### FR-MUT-005
**SHALL** define a `MutationKind` enum with variants covering at minimum `ArithmeticOp`, `LogicalOp`, `RelationalOp`, `ValueSubstitution`, and `StatementDeletion`.
**Traces to**: E3.4
**Source**: `src/mutation/mod.rs:MutationKind`

### FR-MUT-006
**SHALL** serialize `MutationTracker` state to JSON via serde so mutation reports can be persisted between test runs and loaded for trend analysis.
**Traces to**: E3.3
**Source**: `src/mutation/mod.rs:FileCoverage` serde derives

---

## FR-SPEC — Executable Specification Parsing

### FR-SPEC-001
**SHALL** implement `SpecParser::parse_yaml(yaml_str: &str) -> XddResult<Spec>` that deserializes YAML input into a fully-typed `Spec` struct.
**Traces to**: E4.1
**Source**: `src/spec/mod.rs:SpecParser`

### FR-SPEC-002
**SHALL** define `Spec` as a struct with fields `spec: SpecMetadata`, `features: Vec<Feature>` (default empty), and `requirements: Vec<Requirement>` (default empty), all deriving `Serialize`, `Deserialize`, `Debug`, `Clone`.
**Traces to**: E4.2
**Source**: `src/spec/mod.rs:Spec`

### FR-SPEC-003
**SHALL** define `SpecMetadata` with `name: String`, `version: String`, and `description: Option<String>` fields.
**Traces to**: E4.2
**Source**: `src/spec/mod.rs:SpecMetadata`

### FR-SPEC-004
**SHALL** define `Feature` with `id: String`, `name: String`, and `scenario: Option<Scenario>` fields where `Scenario` has optional `given`, `when`, and `then: Option<String>` fields.
**Traces to**: E4.4
**Source**: `src/spec/mod.rs:Feature`

### FR-SPEC-005
**SHALL** implement `SpecValidator::validate(spec: &Spec) -> XddResult<()>` that returns `Err(XddError::SpecValidationError(...))` when any of these conditions are true: `spec.spec.name` is empty, `spec.spec.version` is empty, or any two features share the same `id`.
**Traces to**: E4.3
**Source**: `src/spec/mod.rs:SpecValidator`

### FR-SPEC-006
**SHALL** expose `pub use parser::SpecParser` and `pub use validator::SpecValidator` from `src/spec/mod.rs` so callers import via `phenotype_xdd_lib::spec::{SpecParser, SpecValidator}`.
**Traces to**: E4.1
**Source**: `src/spec/mod.rs`

---

## FR-DOM — Domain Error Types

### FR-DOM-001
**SHALL** define `XddError` as a `thiserror::Error`-derived enum with variants `PropertyTestFailed(String)`, `ContractViolated(String)`, `MutationTrackerError(String)`, `SpecParseError(String)`, and `SpecValidationError(String)`.
**Traces to**: E5.1
**Source**: `src/domain/mod.rs:XddError`

### FR-DOM-002
**SHALL** define `type XddResult<T> = Result<T, XddError>` in `src/domain/mod.rs` and re-export it from `src/lib.rs` so all modules use the shared alias.
**Traces to**: E5.2
**Source**: `src/lib.rs:pub use domain::XddResult`

### FR-DOM-003
**SHALL** re-export `pub use domain::{XddError, XddResult}`, `pub use property::strategies`, and `pub use contract::{Contract, ContractVerifier}` from `src/lib.rs` so the public API is accessible via root crate paths.
**Traces to**: E5.3
**Source**: `src/lib.rs`

### FR-DOM-004
**SHALL** have zero workspace-internal path dependencies — all dependencies are crates.io packages specified in `Cargo.toml`, enabling the crate to be published to crates.io independently.
**Traces to**: E5 (Non-Functional)
**Source**: `Cargo.toml` — no `path = "../"` entries

### FR-DOM-005
**SHALL** pass `cargo clippy -- -D warnings` with zero warnings so code quality is enforced programmatically and not suppressed via `#[allow(...)]` attributes.
**Traces to**: E5 (Non-Functional)
**Source**: Project governance — QA Governance section
