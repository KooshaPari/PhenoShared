#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v cargo-llvm-cov >/dev/null 2>&1; then
  echo "cargo-llvm-cov is required. Install it with: cargo install cargo-llvm-cov --locked" >&2
  exit 1
fi

if ! rustup component list --installed | grep -q '^llvm-tools-preview'; then
  echo "llvm-tools-preview is required. Install it with: rustup component add llvm-tools-preview" >&2
  exit 1
fi

mkdir -p coverage
cargo llvm-cov --workspace --lcov --output-path coverage/lcov.info "$@"
