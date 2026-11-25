# HexaKit standard justfile
# Canonical tier-0 task runner (orch-v12-s1-009)

set shell := ["bash", "-uc"]
set dotenv-load

# Show available recipes
default:
    @just --list

# ─── Build ────────────────────────────────────────────────────────────────────
build:
    cargo build --workspace

build-release:
    cargo build --workspace --release

# ─── Test ─────────────────────────────────────────────────────────────────────
test:
    cargo test --workspace

test-doc:
    cargo test --doc --workspace

# ─── Lint ─────────────────────────────────────────────────────────────────────
lint:
    cargo clippy --workspace --all-targets -- -D warnings
    cargo fmt --all -- --check

# ─── Format ───────────────────────────────────────────────────────────────────
fmt:
    cargo fmt --all

fmt-check:
    cargo fmt --all -- --check

# ─── Audit (cargo-audit / RustSec) ────────────────────────────────────────────
audit:
    cargo audit

# ─── Deny (licenses, advisories, bans, sources) ───────────────────────────────
deny:
    cargo deny check

# ─── Grading (vendored or central grade.sh) ───────────────────────────────────
grade:
    @if [ -f grade.sh ]; then ./grade.sh; \
    elif [ -f ../grade.sh ]; then bash ../grade.sh; \
    else echo "no grade.sh found (vendored or central)"; exit 1; \
    fi

grade-fast:
    @if [ -f grade.sh ]; then ./grade.sh --fast; \
    elif [ -f ../grade.sh ]; then bash ../grade.sh --fast; \
    else echo "no grade.sh found"; exit 1; \
    fi

# ─── Unused dep detection ─────────────────────────────────────────────────────
unused:
    cargo machete

# ─── Documentation ────────────────────────────────────────────────────────────
docs:
    cargo doc --no-deps --workspace

# ─── Full local CI sweep ──────────────────────────────────────────────────────
ci: lint test audit deny unused

# ─── Workspace hygiene ────────────────────────────────────────────────────────
clean:
    cargo clean

update:
    cargo update --workspace

verify: ci
    @echo "✓ Full verification passed"
