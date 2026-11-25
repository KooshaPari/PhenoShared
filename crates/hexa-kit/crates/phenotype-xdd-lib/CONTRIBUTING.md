# Contributing to phenotype-xdd-lib

Thank you for your interest in contributing to phenotype-xdd-lib.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Phenotype-Enterprise/phenotype-xdd-lib
cd phenotype-xdd-lib

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build
cargo build

# Test
cargo test --all-features

# Lint
cargo clippy
cargo fmt --check
```

## Architecture

```
src/
├── domain/          # Pure business logic
├── property/        # Property testing
├── contract/        # Contract testing
├── mutation/        # Mutation tracking
└── spec/           # SpecDD utilities
```

## xDD Methodologies

This library implements multiple xDD methodologies:

- **Property-Based Testing**: Use proptest for generating test cases
- **Contract Testing**: Verify port implementations against contracts
- **Mutation Testing**: Track code coverage with mutation operators
- **SpecDD**: Parse and validate specifications

## Making Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Add property tests for new functionality
5. Add contract tests for port implementations
6. Ensure all checks pass
7. Commit using conventional commits
8. Push and create PR

## Testing Requirements

- All public APIs must have property tests
- Port implementations require contract verification
- Aim for 80% mutation coverage
