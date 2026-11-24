# CI/CD Governance Guide

This document establishes standards and best practices for GitHub Actions workflows across the repos shelf.

## Coverage Thresholds

All projects MUST meet the following coverage requirements:

| Project Type | Minimum Coverage | Target Coverage |
|--------------|------------------|-----------------|
| Libraries (Rust crates) | 85% | 90% |
| Applications/CLIs | 70% | 80% |
| Internal tooling | 50% | 60% |
| Python packages | 80% | 85% |

### Coverage Configuration

**Rust Projects** (using cargo-tarpaulin):
```yaml
- name: Generate coverage
  run: cargo tarpaulin --workspace --out xml --output-dir coverage
- name: Upload to Codecov
  uses: codecov/codecov-action@v4
  with:
    files: ./coverage/cobertura.xml
    flags: rust
    fail_ci_if_error: false
```

**Python Projects** (using pytest-cov):
```yaml
- name: Test with coverage
  run: pytest --cov=. --cov-report=xml
- name: Check threshold
  run: coverage report --fail-under=80
```

## Composite Actions

Use the following reusable composite actions for consistent CI/CD behavior:

### 1. setup-env
Sets up the environment with Rust toolchain, caching, and optional protoc.

```yaml
- uses: ./.github/actions/setup-env
  with:
    rust-version: stable  # or nightly, 1.86.0
    rust-components: rustfmt,clippy
    setup-protoc: 'true'
    workspace: rust
```

### 2. run-tests
Runs tests with optional linting and formatting checks.

```yaml
- uses: ./.github/actions/run-tests
  with:
    test-command: cargo test --workspace
    lint-command: cargo clippy --workspace -- -D warnings
    format-check: 'true'
```

### 3. build-rust-binary
Builds Rust binaries with optional cross-compilation.

```yaml
- uses: ./.github/actions/build-rust-binary
  with:
    target: x86_64-unknown-linux-gnu
    use-cross: 'false'
    binary-name: myapp
```

### 4. security-checks
Runs security scanning tools.

```yaml
- uses: ./.github/actions/security-checks
  with:
    cargo-audit: 'true'
    cargo-deny: 'true'
    gitleaks: 'true'
    python-bandit: 'false'
```

### 5. run-benchmarks
Runs Criterion benchmarks and captures results.

```yaml
- uses: ./.github/actions/run-benchmarks
  with:
    benchmark-dir: benches
    save-artifact: 'true'
```

## Standardized Action Versions

Use these specific versions for consistency:

| Action | Version | Purpose |
|--------|---------|---------|
| actions/checkout | v4 | Code checkout |
| dtolnay/rust-toolchain | stable/nightly | Rust toolchain |
| Swatinem/rust-cache | v2 | Dependency caching |
| arduino/setup-protoc | v3 | Protocol Buffers compiler |
| actions/setup-python | v5 | Python runtime |
| codecov/codecov-action | v4 | Coverage upload |
| actions/upload-artifact | v4 | Artifact handling |
| github/codeql-action | v3 | SAST analysis |
| gitleaks/gitleaks-action | v2 | Secret detection |
| rustsec/audit-check | v2.0.0 | Rust security audit |

## Workflow Patterns

### Branch-Based Stage Gates

| Branch Pattern | Quality Gates |
|----------------|---------------|
| `spike/*` | Format check only |
| `poc/*` | Format + lint |
| `preview/*` | Format + lint + unit tests |
| `main` | Full suite + SAST + coverage |

### Concurrency Control

Always include concurrency settings to cancel redundant runs:

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

### Environment Variables

Standard environment variables for Rust projects:

```yaml
env:
  CARGO_TERM_COLOR: always
  RUSTFLAGS: "-D warnings"
```

## Security Requirements

All projects MUST include:

1. **cargo-audit** - Check for known vulnerabilities in dependencies
2. **cargo-deny** - License compliance and advisory checking
3. **gitleaks** - Secret detection in git history
4. **CodeQL** - Static analysis (for C++, Python, Go, Ruby)

Optional but recommended:
- **OSV-Scanner** - Cross-ecosystem vulnerability scanning
- **bandit** - Python security linting
- **Trivy** - Container image scanning

## Linting Standards

### Rust
- **rustfmt**: `cargo fmt --all -- --check` (hard fail on diff)
- **clippy**: `cargo clippy --workspace -- -D warnings` (deny all warnings)

### Python
- **ruff**: `ruff format --check .` and `ruff check .`
- **bandit**: `bandit -r src -ll` (security linting)
- **pip-audit**: `pip-audit` (dependency vulnerability check)

### TypeScript/JavaScript
- **ESLint**: `npm run lint` or project-specific command
- **oxlint**: Fast alternative for linting

## File Organization

### Workflow File Size Limits
- Maximum: 250 lines per workflow file
- Recommended: ≤150 lines
- Break into multiple workflows if exceeded

### Job Organization
- Maximum: 10 jobs per workflow
- Group related jobs (test, security, release)
- Use matrices for multi-platform testing

### Reusable Workflows
Place reusable workflows in:
- `.github/workflows/` for local reuse
- `templates/workflows/` for project templates
- Separate repository for org-wide sharing

## Migration Notes

### From actions-rs/toolchain
Replace deprecated `actions-rs/toolchain@v1` with:
```yaml
- uses: dtolnay/rust-toolchain@stable
  with:
    components: rustfmt,clippy
```

### From actions/checkout@v6
Standardize on `actions/checkout@v4`:
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # for gitleaks
```

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Rust CI Best Practices](https://doc.rust-lang.org/cargo/guide/continuous-integration.html)
- [Codecov Documentation](https://docs.codecov.com/)
- [cargo-deny Book](https://embarkstudios.github.io/cargo-deny/)
