# Phenotype Fabric — Common development tasks
# ─────────────────────────────────────────────────────────────────────────

.PHONY: check fmt clippy test test-unit test-integration build build-release clean deny docker spawn-core

# ── Quality checks ──────────────────────────────────────────────────────

## Run all quality checks (fmt + clippy + test)
check: fmt clippy test-unit

## Check formatting
fmt:
	cargo fmt --all --check

## Run clippy lints
clippy:
	cargo clippy --workspace --all-targets -- -D warnings

## Run cargo check
verify:
	cargo check --workspace --all-targets

# ── Testing ─────────────────────────────────────────────────────────────

## Run all tests (unit + integration)
test:
	cargo test --workspace --no-fail-fast

## Run unit tests only (fast)
test-unit:
	cargo test --workspace --lib --no-fail-fast

## Run integration tests only
test-integration:
	cargo test --workspace --test '*' --no-fail-fast

## Run a specific test by name
test-%:
	cargo test --workspace --no-fail-fast -- "$*"

# ── Build ───────────────────────────────────────────────────────────────

## Rebuild crates/spawn-core/zig-out/lib/libspawn_core.a from Zig source.
## Needed when that archive is truncated, which surfaces at link time as
## "failed to add native library ...". `ar rcs` appends to an archive that
## already exists, so the bad copy is removed first. Requires `zig` on PATH
## (CI pins 0.15.2 in .github/workflows/quality-gate.yml).
spawn-core:
	mkdir -p crates/spawn-core/zig-out/lib
	cd crates/spawn-core && zig build-obj src/spawn_core.zig -OReleaseSafe -lc -fno-stack-check -femit-bin=zig-out/lib/spawn_core.o
	cd crates/spawn-core && rm -f zig-out/lib/libspawn_core.a && ar rcs zig-out/lib/libspawn_core.a zig-out/lib/spawn_core.o

## Build debug
build:
	cargo build --workspace

## Build release
build-release:
	cargo build --workspace --release --bins

# ── Dependency audit ────────────────────────────────────────────────────

## Run cargo-deny checks
deny:
	cargo deny check

## Install cargo-deny if missing
install-deny:
	cargo install cargo-deny --locked

# ── Docker ──────────────────────────────────────────────────────────────

## Build Docker image locally
docker:
	docker build -t phenotype-fabric:local .

## Run Docker image locally
docker-run: docker
	docker run --rm -p 9400:9400 phenotype-fabric:local

# ── Cleanup ─────────────────────────────────────────────────────────────

## Clean build artifacts
clean:
	cargo clean

## Clean everything including caches
clean-all: clean
	rm -rf target
	find . -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
