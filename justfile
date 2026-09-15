# Phenotype-org standard justfile

default:
    @just --list

# Build workspace
build:
    cargo build --workspace

# Run tests
test:
    cargo test --workspace

# Lint (clippy + fmt --check)
lint:
    cargo clippy --workspace -- -D warnings
    cargo fmt --check

# Format code
fmt:
    cargo fmt

# Security audits (cargo-deny + cargo-audit)
audit:
    cargo deny check
    cargo audit

# Find unused dependencies
unused:
    cargo machete

# Full CI grade (used by lefthook pre-push)
grade: lint test audit unused

# Full local CI sweep
ci: lint test audit unused

# Generate docs
docs:
    cargo doc --no-deps --workspace

# Generate coverage report (requires cargo-llvm-cov: cargo install cargo-llvm-cov --locked)
coverage:
    mkdir -p coverage
    cargo llvm-cov --workspace --lcov --output-path coverage/lcov.info --fail-under-lines 85
    @echo "Coverage report: coverage/lcov.info"

# Generate coverage report without failing (for local dev iteration)
coverage-local:
    mkdir -p coverage
    cargo llvm-cov --workspace --html --output-dir coverage/html
    @echo "HTML report: coverage/html/index.html"

# Generate coverage + open HTML in default browser
coverage-open: coverage-local
    open coverage/html/index.html
