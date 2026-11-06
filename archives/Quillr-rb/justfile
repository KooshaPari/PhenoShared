# Quillr - TypeScript CLI tool
# Native task runner (just)

# Default recipe
default: help

# Help
help:
  @echo "Quillr - TypeScript CLI tool"
  @echo ""
  @just --list

# Install dependencies
install:
  npm install

# Quality checks
check: lint typecheck test
  @echo "All checks passed!"

# Lint
lint:
  npm run lint

# Type check
typecheck:
  npm run typecheck

# Run tests
test:
  npm run test

# Build
build:
  npm run build

# Development
dev:
  npm run dev

# Clean
clean:
  rm -rf dist node_modules/.cache

# Benchmarks
bench:
  npm run bench

# Format
fmt:
  npm run format
