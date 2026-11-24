.PHONY: all install test lint format typecheck clean ci

# Default target
all: test

# Install dependencies
install:
	pnpm install

# Run tests
test:
	pnpm run test

# Run tests with coverage
test-cover:
	pnpm run test:coverage

# Run linter
lint:
	pnpm run lint

# Fix lint issues
lint-fix:
	pnpm run lint:fix

# Format code
format:
	pnpm run format

# Type check
typecheck:
	pnpm run typecheck

# Clean build artifacts
clean:
	rm -rf node_modules/
	rm -rf .next/
	rm -rf dist/
	rm -rf coverage/

# Full CI pipeline
ci: install lint format typecheck test

# Build for production
build:
	pnpm run build

# Development server
dev:
	pnpm run dev

# Run pre-commit checks
pre-commit: lint format typecheck test
