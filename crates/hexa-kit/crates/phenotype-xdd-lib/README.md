# phenotype-xdd-lib

Cross-cutting xDD utilities library for Rust projects.

## Features

- **Property Testing**: Reusable strategies for proptest/quickcheck
- **Contract Testing**: Port/Adapter verification framework
- **Mutation Testing**: Coverage tracking utilities
- **SpecDD**: Specification parsing and validation

## Installation

```toml
[dependencies]
phenotype-xdd-lib = "0.1.0"
```

## Quick Start

```rust
use phenotype_xdd_lib::property::strategies::*;
use phenotype_xdd_lib::contract::{Contract, ContractVerifier};

// Property testing
proptest::prop_assert!(valid_uuid("550e8400-e29b-41d4-a716-446655440000").is_ok());

// Contract testing
trait StoragePort {
    fn get(&self, key: &str) -> Option<String>;
}

struct MemoryStorage;
impl StoragePort for MemoryStorage { ... }

let mut verifier = ContractVerifier::new();
verifier.verify::<MemoryStorage>();
```

## xDD Methodologies

| Category | Methodology | Implementation |
|----------|-------------|----------------|
| Development | TDD | Red-green-refactor cycle |
| Development | BDD | Descriptive test names |
| Development | Property-Based | proptest strategies |
| Development | Contract | Port verification |
| Design | SOLID | Single responsibility |
| Design | DRY | Shared strategies |

## Architecture

```
src/
├── domain/          # Pure business logic
├── property/        # Property testing
├── contract/        # Contract testing
├── mutation/        # Mutation tracking
└── spec/           # SpecDD utilities
```

## License

MIT
