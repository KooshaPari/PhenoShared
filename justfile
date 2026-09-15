# Phenotype-org standard justfile

default:
    @just --list

# ─── Group definitions ──────────────────────────────────────
# 72 workspace members split into 5 groups for faster CI.
# Full workspace builds timeout on cold cache; per-group checks are fast.

PHENOTYPE_CORE := "phenotype-async-traits phenotype-cache-adapter phenotype-casbin-wrapper phenotype-contract phenotype-contracts phenotype-cost-core phenotype-error-core phenotype-error-macros phenotype-errors phenotype-event-sourcing phenotype-flags phenotype-git-core phenotype-health phenotype-http-client-core phenotype-iter phenotype-logging phenotype-macros phenotype-observability phenotype-policy-engine phenotype-port-traits phenotype-ports-canonical phenotype-process phenotype-rate-limit phenotype-retry phenotype-shared-config phenotype-state-machine phenotype-string phenotype-telemetry phenotype-test-infra phenotype-time phenotype-validation phenotype-gfx pheno-runtime-config pheno-context pheno-forge-smoke pheno-config phenotype-config-loader"

AGILE_PLUS := "agileplus-api agileplus-benchmarks agileplus-cache agileplus-cli agileplus-domain agileplus-events agileplus-git agileplus-github agileplus-graph agileplus-grpc agileplus-import agileplus-integration-tests agileplus-nats agileplus-p2p agileplus-plane agileplus-sqlite agileplus-subcmds agileplus-sync agileplus-telemetry agileplus-triage"

EYETRACKER := "eyetracker-domain eyetracker-math eyetracker-core eyetracker-ffi eyetracker-camera eyetracker-inference eyetracker-cli"

OTHER := "bifrost clap-ext clap-ext-examples config-schema configra-ops settly apisync phenoctl"

# ─── Build ──────────────────────────────────────────────────

# Build full workspace (may timeout on cold cache)
build:
    cargo build --workspace

# Build a specific group
build-phenotype:
    cargo check -p {{PHENOTYPE_CORE}}

build-agile:
    cargo check -p {{AGILE_PLUS}}

build-eye:
    cargo check -p {{EYETRACKER}}

build-other:
    cargo check -p {{OTHER}}

# ─── Test ───────────────────────────────────────────────────

# Run all tests (may timeout on cold cache)
test:
    cargo test --workspace

# Test a specific group
test-phenotype:
    cargo test -p {{PHENOTYPE_CORE}}

test-agile:
    cargo test -p {{AGILE_PLUS}}

test-eye:
    cargo test -p {{EYETRACKER}}

test-other:
    cargo test -p {{OTHER}}

# ─── Lint ───────────────────────────────────────────────────

# Lint full workspace (may timeout on cold cache)
lint:
    cargo clippy --workspace -- -D warnings
    cargo fmt --check

# Lint a specific group
lint-phenotype:
    cargo clippy -p {{PHENOTYPE_CORE}} -- -D warnings

lint-agile:
    cargo clippy -p {{AGILE_PLUS}} -- -D warnings

lint-eye:
    cargo clippy -p {{EYETRACKER}} -- -D warnings

lint-other:
    cargo clippy -p {{OTHER}} -- -D warnings

# ─── Format ─────────────────────────────────────────────────

fmt:
    cargo fmt

# ─── Audit ──────────────────────────────────────────────────

audit:
    cargo deny check
    cargo audit

# ─── Unused deps ────────────────────────────────────────────

unused:
    cargo machete

# ─── Combined targets ───────────────────────────────────────

# Full CI grade (used by lefthook pre-push) -- runs workspace-wide
grade: lint test audit unused

# Fast grade: per-group checks (avoids workspace timeout)
grade-fast:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "=== Lint: phenotype-core ==="
    cargo clippy -p {{PHENOTYPE_CORE}} -- -D warnings 2>&1 | tail -3
    echo "=== Lint: agile-plus ==="
    cargo clippy -p {{AGILE_PLUS}} -- -D warnings 2>&1 | tail -3
    echo "=== Lint: eyetracker ==="
    cargo clippy -p {{EYETRACKER}} -- -D warnings 2>&1 | tail -3
    echo "=== Lint: other ==="
    cargo clippy -p {{OTHER}} -- -D warnings 2>&1 | tail -3
    echo "=== Fmt ==="
    cargo fmt --check
    echo "=== Audit ==="
    cargo deny check 2>&1 | tail -5
    cargo audit 2>&1 | tail -5
    echo "=== Unused ==="
    cargo machete 2>&1 | tail -3
    echo "=== ALL PASSED ==="

# Lint only (fast, per-group)
lint-fast:
    #!/usr/bin/env bash
    set -euo pipefail
    cargo clippy -p {{PHENOTYPE_CORE}} -- -D warnings 2>&1 | tail -2
    cargo clippy -p {{AGILE_PLUS}} -- -D warnings 2>&1 | tail -2
    cargo clippy -p {{EYETRACKER}} -- -D warnings 2>&1 | tail -2
    cargo clippy -p {{OTHER}} -- -D warnings 2>&1 | tail -2
    cargo fmt --check
    echo "Lint passed"

# Test only (fast, per-group)
test-fast:
    #!/usr/bin/env bash
    set -euo pipefail
    cargo test -p {{PHENOTYPE_CORE}} 2>&1 | tail -3
    cargo test -p {{AGILE_PLUS}} 2>&1 | tail -3
    cargo test -p {{EYETRACKER}} 2>&1 | tail -3
    cargo test -p {{OTHER}} 2>&1 | tail -3
    echo "Tests passed"

# ─── Docs ───────────────────────────────────────────────────

docs:
    cargo doc --no-deps --workspace

# ─── Coverage ───────────────────────────────────────────────

coverage:
    mkdir -p coverage
    cargo llvm-cov --workspace --lcov --output-path coverage/lcov.info --fail-under-lines 85
    @echo "Coverage report: coverage/lcov.info"

coverage-local:
    mkdir -p coverage
    cargo llvm-cov --workspace --html --output-dir coverage/html
    @echo "HTML report: coverage/html/index.html"

coverage-open: coverage-local
    open coverage/html/index.html
