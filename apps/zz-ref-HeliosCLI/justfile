# justfile — HeliosCLI
# Task runner for governance, lint, test, and release workflows.
# Install: https://github.com/casey/just
# Run `just` (no args) to list available recipes.

set shell := ["bash", "-uc"]

# Default recipe — show available recipes
default:
    @just --list

# ─── Governance ────────────────────────────────────────────────────────────

# Verify CODEOWNERS has @kooshapari for "*"
verify-codeowners:
    @grep -E '^\s*\*\s+@kooshapari' .github/CODEOWNERS >/dev/null \
        && echo "✓ CODEOWNERS: @kooshapari owns *" \
        || (echo "✗ CODEOWNERS missing @kooshapari for *" && exit 1)

# Verify required governance files exist
verify-governance:
    @test -f .github/CODEOWNERS           && echo "✓ .github/CODEOWNERS"            || (echo "✗ missing .github/CODEOWNERS"            && exit 1)
    @test -f .github/pull_request_template.md && echo "✓ .github/pull_request_template.md" || (echo "✗ missing .github/pull_request_template.md" && exit 1)
    @test -d .github/ISSUE_TEMPLATE       && echo "✓ .github/ISSUE_TEMPLATE/"      || (echo "✗ missing .github/ISSUE_TEMPLATE/"       && exit 1)
    @test -f justfile                     && echo "✓ justfile"                     || (echo "✗ missing justfile"                     && exit 1)
    @test -f CHANGELOG.md                 && echo "✓ CHANGELOG.md"                 || (echo "✗ missing CHANGELOG.md"                 && exit 1)

# ─── Build / Test ──────────────────────────────────────────────────────────

# Type-check the Rust workspace (no codegen)
check:
    cargo check --workspace --all-targets

# Build the workspace
build:
    cargo build --workspace

# Run the test suite
test:
    cargo test --workspace

# Compile each Rust benchmark and execute it once without measuring performance.
# The `Format / etc` CI job runs this from codex-rs/, which has no justfile of
# its own, so `just` walks up to this one.
bench-smoke:
    cargo bench --manifest-path codex-rs/Cargo.toml -p codex-utils-image --bench prompt_images -- --test

# Run clippy with warnings as errors
lint:
    cargo clippy --workspace --all-targets -- -D warnings

# Format check
fmt-check:
    cargo fmt --all -- --check

# ─── Hygiene ───────────────────────────────────────────────────────────────

# Run all governance + hygiene checks
audit: verify-codeowners verify-governance
    @echo "All governance checks passed."

# ─── Release ───────────────────────────────────────────────────────────────

# Show the next semantic version given current CHANGELOG state
version:
    @grep -E '^## ' CHANGELOG.md | head -1 | sed 's/^## //'

# ─── Meta ──────────────────────────────────────────────────────────────────

# Show repo metadata
meta:
    @echo "branch:    $(git branch --show-current)"
    @echo "remote:    $(git remote get-url origin 2>/dev/null || echo none)"
    @echo "HEAD:      $(git rev-parse --short HEAD)"
