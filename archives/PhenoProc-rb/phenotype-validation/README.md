# phenotype-validation — Schema & Rule Validation Engine

Lightweight, composable validation framework for process I/O and schema enforcement across the Phenotype ecosystem. Provides JSON schema validation, custom rule evaluation, and error aggregation with minimal overhead.

## Overview

**phenotype-validation** decouples validation logic from business code, enabling declarative, reusable validation pipelines. It supports JSON Schema, custom rule engines, and extensible validator chains for both structured and unstructured data validation.

**Core Mission**: Enable safe, predictable data validation without runtime dependencies on heavy frameworks, maintaining composability across heterogeneous process boundaries.

## Technology Stack

- **Language**: Rust (Edition 2021)
- **Schema Support**: JSON Schema draft-7, serde_json
- **Rule Engine**: Custom evaluator with predicate composition
- **Error Handling**: Aggregated validation errors with context
- **Testing**: Inline unit tests, integration test fixtures

## Key Features

- **JSON Schema Validation**: Full draft-7 compliance with custom format validators
- **Custom Rule Evaluation**: Predicate-based rules with boolean composition
- **Error Aggregation**: Collect multiple validation failures per data structure
- **Type-Safe Builders**: Fluent API for composing validation pipelines
- **Zero-Copy Validation**: Minimal allocations for performance-critical paths
- **Extensible Validators**: Trait-based system for custom validation logic
- **Serde Integration**: Automatic schema derivation from Rust types

## Quick Start

```bash
# Navigate to sub-crate
cd /Users/kooshapari/CodeProjects/Phenotype/repos/PhenoProc/phenotype-validation

# Build and test
cargo build
cargo test --lib

# Run example validator
cargo run --example validate_config -- examples/sample.json

# Check for lint warnings
cargo clippy -- -D warnings
```

## Project Structure

```
phenotype-validation/
├── Cargo.toml
├── src/
│   ├── lib.rs                    # Public API, Validator trait
│   ├── schema.rs                 # JSON Schema validator
│   ├── rules.rs                  # Custom rule evaluator
│   ├── error.rs                  # Validation error types
│   └── builders.rs               # Fluent validator builders
├── examples/
│   ├── validate_config.rs        # Configuration validation example
│   └── custom_rules.rs           # Custom rule composition
├── tests/
│   ├── integration_tests.rs      # End-to-end validation scenarios
│   └── fixtures/
├── CLAUDE.md                     # Governance
└── README.md                     # This file
```

## Related Phenotype Projects

- **PhenoProc** — Parent monorepo; process orchestration core
- **phenotype-config-ts** — Configuration management with validation integration
- **phenotype-router-monitor** — Applies validation to request/response payloads

## License & Governance

Licensed under Apache 2.0. See `LICENSE` in parent. Governance in `CLAUDE.md`. Functional requirements and FR-to-test mapping in `FUNCTIONAL_REQUIREMENTS.md`.
