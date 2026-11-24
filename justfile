# justfile — phenotype-landing developer task runner
# https://github.com/casey/just
#
# Mirrors Taskfile.yml commands for CI-local reproduction.
# Install:  brew install just   |   cargo install just

set dotenv-load := false
set shell := ["bash", "-uc"]

sites := "tracera-landing agileplus-landing byteport-landing hwledger-landing phenokits-landing projects-landing thegent-landing"

default:
    @just --list

# Install dependencies for all sites
install:
    @for site in {{sites}}; do \
        (cd sites/$$site && bun install --frozen-lockfile || bun install); \
    done

# Build all Astro sites
build:
    @for site in {{sites}}; do \
        echo "=== $$site ===" && (cd sites/$$site && bun run build); \
    done

# Type-check all Astro sites
check:
    @for site in {{sites}}; do \
        echo "=== $$site ===" && (cd sites/$$site && bunx astro check); \
    done

# Lint all Astro sites (best-effort)
lint:
    @for site in {{sites}}; do \
        echo "=== $$site ===" && (cd sites/$$site && bunx astro check); \
    done

# Full quality gate: check + build + lint
quality: check build lint

# Dependency audit via cargo-deny. No-op for the Astro/JS sites since
# phenotype-landing has no Rust crate dependencies; the recipe is kept
# for org-wide SSOT alignment and to gate any future Rust surface.
deny:
    @if [ -f Cargo.toml ]; then \
        cargo deny check; \
    else \
        echo "deny: no Cargo.toml found in $(pwd) — skipping (Astro/JS monorepo)"; \
    fi

# Remove build artifacts
clean:
    rm -rf sites/*/dist sites/*/.astro

# Run the full CI suite locally
ci: install check build
