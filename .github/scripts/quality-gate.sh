#!/usr/bin/env bash
# quality-gate.sh — runs clippy, fmt check, and optionally cargo test
set -euo pipefail

echo "=== Clippy ==="
cargo clippy --workspace --all-targets -- -D warnings

echo "=== Format check ==="
cargo fmt --check

echo "=== Tests ==="
cargo test --workspace

echo "=== All quality gates passed ==="
