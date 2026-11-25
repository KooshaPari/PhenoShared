# AGENTS.md - phenotype-xdd-lib

## Project Overview

- **Name**: phenotype-xdd-lib
- **Description**: Cross-cutting xDD utilities library for Rust projects
- **Language**: Rust (edition 2021)
- **Location**: Phenotype repos shelf

## Features

- **Property Testing**: Reusable strategies for proptest/quickcheck
- **Contract Testing**: Port/Adapter verification framework
- **Mutation Testing**: Coverage tracking utilities
- **SpecDD**: Specification parsing and validation

## Agent Rules

### Project-Specific Rules

1. **xDD Implementation**
   - Property-based tests using proptest
   - Contract tests for port verification
   - Mutation coverage tracking
   - SpecDD for specification validation

2. **Code Organization**
   ```
   src/
   ├── domain/          # Pure business logic
   ├── property/        # Property testing
   ├── contract/        # Contract testing
   ├── mutation/        # Mutation tracking
   └── spec/           # SpecDD utilities
   ```

3. **Testing Requirements**
   - All public APIs must have property tests
   - Port implementations require contract verification
   - Aim for 80% mutation coverage

### Phenotype Org Standard Rules

1. **UTF-8 encoding** in all text files
2. **Worktree discipline**: canonical repo stays on `main`
3. **CI completeness**: fix all CI failures before merging
4. **Never commit** agent directories (`.claude/`, `.codex/`, `.cursor/`)

## Quality Standards

```bash
# Build
cargo build

# Test with all features
cargo test --all-features

# Lint
cargo clippy -- -D warnings

# Format
cargo fmt --check
```

## Git Workflow

1. Create feature branch: `git checkout -b feat/my-feature`
2. Add property tests for new functionality
3. Add contract tests for port implementations
4. Run full test suite
5. Create PR with test coverage report
