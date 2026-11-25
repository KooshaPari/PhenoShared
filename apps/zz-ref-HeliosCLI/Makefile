# Helios CLI — Rust Workspace Makefile
# Usage: make help

.PHONY: help build test test-unit test-integration bench lint fmt clippy \
        clean coverage security-scan fmt-check clippy-fix pre-commit-install \
        pre-commit qa doc check \
        otel-deploy otel-teardown otel-health otel-logs otel-ps

CARGO := cargo
CARGOFLAGS := --workspace
COVERPROFILE := coverage.out
COVERHTML := coverage.html

# ──────────────────────────────────────────────
# Help
# ──────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────
# Build
# ──────────────────────────────────────────────

build: ## Build all workspace crates
	$(CARGO) build $(CARGOFLAGS)

build-release: ## Build all workspace crates (release)
	$(CARGO) build $(CARGOFLAGS) --release

# ──────────────────────────────────────────────
# Testing
# ──────────────────────────────────────────────

test: ## Run all tests
	$(CARGO) test $(CARGOFLAGS)

test-unit: ## Run unit tests only
	$(CARGO) test $(CARGOFLAGS) --lib

test-integration: ## Run integration tests only
	$(CARGO) test $(CARGOFLAGS) --test '*'

test-specific: ## Run a specific test (TEST=name make test-specific)
	$(CARGO) test $(CARGOFLAGS) $(TEST) -- --nocapture

bench: ## Run benchmarks
	$(CARGO) bench $(CARGOFLAGS)

test-ignored: ## Run ignored tests
	$(CARGO) test $(CARGOFLAGS) -- --ignored

# ──────────────────────────────────────────────
# Linting & Formatting
# ──────────────────────────────────────────────

lint: clippy ## Alias for clippy

clippy: ## Run clippy (all targets, all features)
	$(CARGO) clippy $(CARGOFLAGS) --all-targets --all-features -- -D warnings

clippy-fix: ## Run clippy with auto-fix
	$(CARGO) clippy $(CARGOFLAGS) --all-targets --all-features --fix --allow-dirty

fmt: ## Format all Rust code
	$(CARGO) fmt $(CARGOFLAGS)

fmt-check: ## Check formatting without modifying
	$(CARGO) fmt $(CARGOFLAGS) -- --check

check: ## Run cargo check (faster than build for syntax/type errors)
	$(CARGO) check $(CARGOFLAGS)

# ──────────────────────────────────────────────
# Coverage
# ──────────────────────────────────────────────

coverage: ## Run tests with coverage (requires cargo-tarpaulin)
	@command -v cargo-tarpaulin >/dev/null 2>&1 || \
		(echo "Installing cargo-tarpaulin..." && $(CARGO) install cargo-tarpaulin)
	$(CARGO) tarpaulin $(CARGOFLAGS) --out Html --output-dir coverage-html --skip-clean
	@echo "Coverage report: coverage-html/tarpaulin-report.html"

coverage-local: ## Generate local coverage report
	$(CARGO) llvm-cov $(CARGOFLAGS) --html --output-dir coverage-html 2>/dev/null || \
		(echo "Falling back to tarpaulin..." && $(CARGO) tarpaulin $(CARGOFLAGS) --out Html --output-dir coverage-html)

# ──────────────────────────────────────────────
# Security
# ──────────────────────────────────────────────

security-scan: ## Run security scans
	@echo "Running cargo-audit..."
	@command -v cargo-audit >/dev/null 2>&1 && $(CARGO) audit || \
		(echo "cargo-audit not installed, installing..." && $(CARGO) install cargo-audit && $(CARGO) audit)
	@echo "Running gitleaks..."
	-gitleaks detect --source . --verbose
	@echo "Security scan complete."

# ──────────────────────────────────────────────
# Documentation
# ──────────────────────────────────────────────

doc: ## Generate documentation
	$(CARGO) doc $(CARGOFLAGS) --no-deps

doc-open: ## Generate and open documentation
	$(CARGO) doc $(CARGOFLAGS) --no-deps --open

# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────

clean: ## Remove build artifacts
	$(CARGO) clean
	rm -rf coverage-html/ $(COVERPROFILE)

clean-all: clean ## Remove build artifacts and target directory
	rm -rf target/

# ──────────────────────────────────────────────
# Pre-commit
# ──────────────────────────────────────────────

pre-commit-install: ## Install pre-commit hooks
	pre-commit install
	pre-commit install --hook-type commit-msg

pre-commit: ## Run all pre-commit hooks
	pre-commit run --all-files

# ──────────────────────────────────────────────
# Full QA
# ──────────────────────────────────────────────

qa: fmt-check clippy test coverage security-scan ## Full quality assurance suite
	@echo "All QA checks passed."

# ──────────────────────────────────────────────
# OTel / Observability Stack
# ──────────────────────────────────────────────

otel-deploy: ## Deploy production OTel collector stack
	@bash deploy/deploy.sh

otel-teardown: ## Tear down OTel stack (containers only)
	@bash deploy/teardown.sh

otel-teardown-all: ## Tear down OTel stack, volumes, and images
	@bash deploy/teardown.sh --all

otel-health: ## Run OTel stack health checks
	@bash deploy/health-check.sh

otel-logs: ## Tail logs from all OTel services
	docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env logs -f

otel-ps: ## Show OTel stack status
	docker compose -f deploy/docker-compose.production.yml --env-file deploy/.env ps
