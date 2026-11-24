# ADR-001: phenotype-xdd-lib Architecture

**Status**: Accepted
**Date**: 2026-03-25

## Context

We need a cross-cutting library for xDD (executable development methodologies) practices that can be shared across all Phenotype ecosystem projects in multiple languages (Rust, Go, Python, TypeScript, Zig).

## Decision

Create `phenotype-xdd-lib` as a Rust library providing:

1. **Property Testing Strategies**: Reusable strategies for proptest/quickcheck
2. **Contract Testing**: Port/Adapter verification framework
3. **Mutation Testing Utilities**: Coverage tracking helpers
4. **SpecDD**: Specification parsing and validation

## Architecture

### Hexagonal/Clean Architecture

```
┌─────────────────────────────────────────────────┐
│                  Domain Layer                     │
│  (Pure business logic, no external deps)        │
│  - XddError, XddResult                         │
│  - ErrorCategory                                │
├─────────────────────────────────────────────────┤
│                Application Layer                  │
│  (Use cases, ports interfaces)                  │
│  - Contract, ContractVerifier                   │
│  - MutationTracker, CoverageReport              │
│  - Spec, SpecValidator                         │
├─────────────────────────────────────────────────┤
│              Infrastructure Layer                 │
│  (External adapters)                            │
│  - proptest strategies                         │
│  - serde_yaml parsing                          │
└─────────────────────────────────────────────────┘
```

### Module Structure

```
src/
├── lib.rs              # Public API, re-exports
├── domain/
│   └── mod.rs         # XddError, XddResult, ErrorCategory
├── property/
│   ├── mod.rs         # Property module
│   └── strategies.rs   # Reusable strategies
├── contract/
│   └── mod.rs         # Contract testing framework
├── mutation/
│   └── mod.rs         # Mutation tracking utilities
└── spec/
    ├── mod.rs         # Spec structures
    ├── parser.rs      # YAML parsing
    └── validator.rs   # Validation logic
```

## xDD Methodologies Applied

| Category | Methodology | Implementation |
|----------|-------------|----------------|
| **Development** | TDD | Red-green-refactor cycle, tests first |
| **Development** | BDD | Descriptive test names with Given/When/Then |
| **Development** | Property-Based | proptest strategies |
| **Development** | Contract | Port verification via Contract trait |
| **Design** | SOLID | Single responsibility per module |
| **Design** | DRY | Shared strategies, no duplication |
| **Design** | KISS | Simple trait/function signatures |
| **Design** | PoLA | Descriptive error messages |

## Consequences

### Positive
- Shared xDD utilities across Rust projects
- Consistent error handling across ecosystem
- Contract testing ensures adapter compliance

### Negative
- Adds external dependency on proptest
- May need feature flags for different use cases

## Alternatives Considered

### 1. External Crates
**Rejected**: Existing crates (proptest, quickcheck) don't provide contract testing in a reusable way.

### 2. Inline Implementation
**Rejected**: Duplication across projects, harder to maintain consistency.

## References

- [proptest book](https://altsysrq.github.io/proptest-book/)
- [Contract Testing - Pact](https://docs.pact.io/)
- [Hexagonal Architecture](http://alistair.cockburn.us/hexagonal+architecture)
