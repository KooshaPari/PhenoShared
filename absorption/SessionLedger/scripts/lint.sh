#!/bin/sh
# Ecosystem-standard lint script
set -e

echo "Running ecosystem linters..."

if command -v cargo >/dev/null 2>&1 && [ -f Cargo.toml ]; then
  echo "Running cargo fmt --check..."
  cargo fmt --check || { echo "cargo fmt check failed. Run 'cargo fmt' to fix."; exit 1; }
  echo "Running cargo clippy..."
  cargo clippy -- -D warnings || { echo "cargo clippy failed."; exit 1; }
fi

if command -v ruff >/dev/null 2>&1 && [ -f pyproject.toml ]; then
  echo "Running ruff check..."
  ruff check . || { echo "ruff check failed. Run 'ruff check --fix .' to fix."; exit 1; }
fi
