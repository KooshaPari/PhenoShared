# GitHub Actions Composite Actions

This directory contains reusable composite actions that consolidate common CI/CD patterns across the repos shelf.

## Available Actions

| Action | Purpose | Key Inputs |
|--------|---------|------------|
| [setup-env](./setup-env) | Setup Rust toolchain, caching, protoc | `rust-version`, `setup-protoc`, `checkout-depth` |
| [run-tests](./run-tests) | Run tests with optional linting | `test-command`, `lint-command`, `skip-lint` |
| [build-rust-binary](./build-rust-binary) | Build Rust binaries with cross-compilation | `target`, `use-cross`, `binary-name` |
| [security-checks](./security-checks) | Run security scanning tools | `cargo-audit`, `cargo-deny`, `gitleaks` |
| [run-benchmarks](./run-benchmarks) | Run Criterion benchmarks | `benchmark-dir`, `tool`, `output-file` |

## Quick Start

### Simple Test & Lint

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: ./.github/actions/setup-env
      - uses: ./.github/actions/run-tests
```

### Cross-Platform Release Build

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        target: [x86_64-unknown-linux-gnu, x86_64-apple-darwin]
    steps:
      - uses: ./.github/actions/setup-env
        with:
          rust-version: stable
          setup-protoc: 'true'

      - uses: ./.github/actions/build-rust-binary
        with:
          target: ${{ matrix.target }}
          use-cross: ${{ matrix.target != 'x86_64-unknown-linux-gnu' }}
```

### Full Security Scan

```yaml
jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: ./.github/actions/setup-env
        with:
          checkout-depth: '0'  # full history for gitleaks

      - uses: ./.github/actions/security-checks
        with:
          cargo-audit: 'true'
          cargo-deny: 'true'
          gitleaks: 'true'
```

## Default Values

Each action has sensible defaults:

### setup-env
- `rust-version`: stable
- `setup-protoc`: false
- `checkout-depth`: 1
- `rust-components`: (empty)

### run-tests
- `test-command`: cargo test --all
- `lint-command`: cargo clippy -- -D warnings
- `skip-lint`: false
- `format-check`: true

### build-rust-binary
- `use-cross`: false
- `binary-name`: agileplus
- `strip-binary`: true
- `release`: true

### security-checks
- `cargo-audit`: true
- `cargo-deny`: true
- `gitleaks`: true
- `python-bandit`: false

### run-benchmarks
- `benchmark-dir`: benches
- `tool`: cargo
- `output-file`: target/criterion/output.txt
- `save-artifact`: true

## Using with Reusable Workflows

For more complex scenarios, use the [reusable workflows](../workflows/reusable/):

```yaml
jobs:
  quality:
    uses: ./.github/workflows/reusable/rust-quality.yml
    with:
      rust-version: stable
      workspace: .
```

## Migration Guide

### From Direct Action Usage

Replace repetitive action sequences:

**Before:**
```yaml
steps:
  - uses: actions/checkout@v4
  - uses: dtolnay/rust-toolchain@stable
    with:
      components: rustfmt,clippy
  - uses: Swatinem/rust-cache@v2
  - uses: arduino/setup-protoc@v3
```

**After:**
```yaml
steps:
  - uses: ./.github/actions/setup-env
    with:
      rust-components: rustfmt,clippy
      setup-protoc: 'true'
```

## See Also

- [GOVERNANCE.md](../GOVERNANCE.md) - CI/CD standards and coverage thresholds
- [QUICK_REFERENCE.md](../QUICK_REFERENCE.md) - Quick reference for workflow patterns
