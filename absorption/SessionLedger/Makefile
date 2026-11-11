# SessionLedger developer task surface
# Prefer `just` / `task` when installed; recipes below remain the fallback.
# Aligns with AGENTS.md / .github/workflows/ci.yml where noted.

CARGO ?= cargo
DAEMON_MANIFEST := crates/sl-daemon/Cargo.toml

# Use `just` when available (GNU make / POSIX shells).
JUST := $(shell command -v just 2>/dev/null)

.PHONY: help build test lint fmt clippy package seed bench-gate bench-gate-check bench-gate-latency dev dev-down up

ifdef JUST

help:
	@$(JUST) --list

build:
	@$(JUST) build

test:
	@$(JUST) test

lint:
	@$(JUST) lint

fmt:
	@$(JUST) fmt

clippy:
	@$(JUST) clippy

package:
	@$(JUST) package

seed:
	@$(JUST) seed

bench-gate:
	@$(JUST) bench-gate

bench-gate-check:
	@$(JUST) bench-gate-check

bench-gate-latency:
	@$(JUST) bench-gate-latency

up:
	@$(JUST) up

dev:
	@$(JUST) dev

dev-down:
	@$(JUST) dev-down

else

help:
	@echo "Targets (install \`just\` for the preferred runner):"
	@echo "  build     compile sl-daemon and sl-viewer (debug)"
	@echo "  test      cargo test --all-features --locked (+ daemon)"
	@echo "  fmt       apply rustfmt (workspace + daemon)"
	@echo "  clippy    cargo clippy --all-targets --all-features"
	@echo "  lint      fmt --check + clippy (CI-equivalent gate)"
	@echo "  package   desktop packaging (packaging/Makefile)"
	@echo "  seed      copy a sample OKF fixture into SL_DATA_DIR (default .sl-data)"
	@echo "  bench-gate        enforced pipeline Criterion perf-budget gate"
	@echo "  bench-gate-check  perf-budget policy SelfCheck (no cargo bench)"
	@echo "  bench-gate-latency soft C00 L6 p95 latency SelfCheck"
	@echo "  up        runtime-up script if present, else process-compose up"
	@echo "  dev       build then up"
	@echo "  dev-down  process-compose down"

## build - compile sl-daemon and sl-viewer (debug profile)
build:
	$(CARGO) build --manifest-path $(DAEMON_MANIFEST)
	$(CARGO) build -p sl-viewer

## test - workspace suite (CI flags) plus excluded sl-daemon
test:
	$(CARGO) test --all-features --locked
	$(CARGO) test --manifest-path $(DAEMON_MANIFEST)

## fmt - apply rustfmt across workspace + daemon
fmt:
	$(CARGO) fmt --all
	$(CARGO) fmt --manifest-path $(DAEMON_MANIFEST)

## clippy - lint with clippy (workspace + daemon)
clippy:
	$(CARGO) clippy --all-targets --all-features --locked
	$(CARGO) clippy --manifest-path $(DAEMON_MANIFEST) --all-targets

## lint - format check + clippy (matches CI rustfmt/clippy steps)
lint:
	$(CARGO) fmt --all --check
	$(CARGO) fmt --manifest-path $(DAEMON_MANIFEST) --check
	$(CARGO) clippy --all-targets --all-features --locked
	$(CARGO) clippy --manifest-path $(DAEMON_MANIFEST) --all-targets

## package - desktop packaging via packaging/Makefile
package:
	$(MAKE) -C packaging package-all

## seed - copy a sample OKF fixture into SL_DATA_DIR (default .sl-data)
seed:
	pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/seed-sample.ps1

## bench-gate - enforced pipeline Criterion perf-budget gate (blocking)
bench-gate:
	pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/bench-gate.ps1

## bench-gate-check - validate enforced budget policy without cargo bench
bench-gate-check:
	pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/bench-gate.ps1 -SelfCheck

## bench-gate-latency - soft C00 L6 p95 latency baseline SelfCheck
bench-gate-latency:
	pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/bench-gate.ps1 -SoftLatencyCheck

## up - runtime-up script if present, else process-compose
up:
	@if [ -f scripts/runtime-up.ps1 ]; then \
		pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/runtime-up.ps1; \
	elif [ -f scripts/runtime-up.sh ]; then \
		bash scripts/runtime-up.sh; \
	else \
		process-compose up; \
	fi

## dev - build both crates then bring up the local stack
dev: build
	@$(MAKE) up

## dev-down - tear down the process-compose stack
dev-down:
	process-compose down

endif
