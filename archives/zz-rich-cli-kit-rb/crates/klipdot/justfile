# KlipDot Justfile — Phenotype-org tier-0 hygiene
# Source: https://github.com/KooshaPari/phenotype-tooling/blob/main/templates/justfile-rust
#
# Run `just` (no args) to list available recipes.

set shell := ["bash", "-euo", "pipefail", "-c"]
set dotenv-load := true

# Default recipe — list available commands.
default:
    @just --list

# ─── Tier-0 umbrella ────────────────────────────────────────────────────────

# Run the full tier-0 hygiene sweep locally (fmt + clippy + deny + audit + pre-commit).
tier0: fmt-check lint deny audit pre-commit
    @echo "tier-0 hygiene passed"

# ─── Build & test ───────────────────────────────────────────────────────────

# Build the workspace (debug).
build:
    cargo build --workspace

# Build the workspace (release).
build-release:
    cargo build --workspace --release

# Run all tests.
test:
    cargo test --workspace

# Run tests for one crate by name (usage: just test-one klipdot).
test-one name:
    cargo test -p {{name}}

# ─── Formatting & linting ───────────────────────────────────────────────────

# Auto-format code in place.
fmt:
    cargo fmt --all

# Check formatting without modifying files.
fmt-check:
    cargo fmt --all -- --check

# Run clippy on the workspace, treating warnings as errors.
lint:
    cargo clippy --workspace --all-targets --all-features -- -D warnings

# Run clippy without failing on warnings (used in CI gating).
lint-soft:
    cargo clippy --workspace --all-targets --all-features

# ─── Supply-chain & security ───────────────────────────────────────────────

# Run cargo-deny against the workspace (advisories, licenses, bans, sources).
deny:
    cargo deny check

# Run cargo-audit on the dependency tree.
audit:
    cargo audit

# Run trufflehog secret scan (if installed).
secrets:
    @command -v trufflehog >/dev/null && trufflehog git file://. --only-verified || echo "trufflehog not installed; skipping"

# ─── CI-like aggregate ─────────────────────────────────────────────────────

# Aggregate CI command — build + test + lint.
ci: build test lint
    @echo "ci passed"

# ─── Hooks & hooks installation ─────────────────────────────────────────────

# Run all pre-commit hooks against the working tree.
pre-commit:
    @command -v pre-commit >/dev/null && pre-commit run --all-files || echo "pre-commit not installed; skipping"

# Install pre-commit hooks into .git/hooks.
hooks:
    @command -v pre-commit >/dev/null && pre-commit install || echo "pre-commit not installed; skipping"

# ─── Docs & diagrams ────────────────────────────────────────────────────────

# Build rustdoc for the workspace.
docs:
    cargo doc --workspace --no-deps

# Validate cross-doc link integrity (uses the local doc-links workflow).
doc-links:
    @echo "validate doc-links via .github/workflows/doc-links.yml"

# ─── Release & publishing ───────────────────────────────────────────────────

# Dry-run release (bump version, generate notes, do not publish).
release-dry:
    @echo "release dry-run: bump VERSION, render CHANGELOG, no publish"

# ─── Maintenance ────────────────────────────────────────────────────────────

# Clean build artifacts.
clean:
    cargo clean

# Update the Cargo.lock to the latest compatible versions.
update:
    cargo update

# Audit + print a one-line status summary.
status:
    @echo "branch: $(git branch --show-current)"
    @echo "commit: $(git rev-parse --short HEAD)"
    @echo "status: $(git status --porcelain | wc -l | tr -d ' ') dirty files"
