# Architecture Decision Records — phenotype-xdd-lib

## ADR-001 — Rust Proc-Macro for Contract Tests

**Status:** Accepted  
**Date:** 2026-03-27

### Context
Generating conformance test suites for port adapters requires repetitive boilerplate. A proc-macro eliminates this at compile time.

### Decision
Implement `#[contract_test]` as a Rust procedural macro in a `phenotype-xdd-lib-macros` sub-crate. The macro expands to a `#[cfg(test)]` module with generated test functions.

### Consequences
- Zero-cost abstraction: no runtime overhead.
- Macro compilation errors are reported at the call site with spans.

---

## ADR-002 — Proptest as Property Testing Backend

**Status:** Accepted  
**Date:** 2026-03-27

### Context
Quickcheck and proptest are the two dominant property testing libraries in Rust. Proptest has richer strategy composition and better shrinking.

### Decision
Build xdd-lib property testing on proptest 1.x. All strategies implement `proptest::strategy::Strategy`.

### Consequences
- Users must add proptest as a dev-dependency.
- xdd-lib strategies compose with user-defined proptest strategies.

---

## ADR-003 — SpecDD as a Build-Time Tool

**Status:** Accepted  
**Date:** 2026-03-27

### Context
FR traceability checks should run at build time, not as a separate audit tool.

### Decision
SpecDD validation runs as a Cargo `build.rs` step or a `cargo xtask` command. It reads spec Markdown files and test source via `cargo metadata`.

### Consequences
- Traceability is enforced on every `cargo test`.
- CI does not need a separate audit step.
