# phenotype-infra top-level Makefile
# Polyglot build orchestration for Go + Rust workspace

.PHONY: help nvms-c-archive cargo-check cargo-test cargo-clippy cargo-fmt

GO := go
CARGO := cargo

help:
	@echo "phenotype-infra Makefile"
	@echo "  make nvms-c-archive   - Build Go static lib (libnvms_core.a)"
	@echo "  make cargo-check      - cargo check --workspace"
	@echo "  make cargo-test       - cargo test --workspace"
	@echo "  make cargo-clippy     - cargo clippy --workspace"
	@echo "  make cargo-fmt        - cargo fmt --check"
	@echo "  make go-vet           - go vet on nanovms-core"
	@echo "  make go-test          - go test on nanovms-core"

# Build Go static library via CGo
nvms-c-archive:
	cd crates\nanovms-core\bindings\go-c-export && $(GO) build -buildmode=c-archive -o ../../../target/libnvms_core.a .
	@echo "libnvms_core.a built at target/libnvms_core.a"

# Rust checks
cargo-check:
	$(CARGO) check --workspace

cargo-test:
	$(CARGO) test --workspace

cargo-clippy:
	$(CARGO) clippy --workspace -- -D warnings

cargo-fmt:
	$(CARGO) fmt -- --check

# Go checks
go-vet:
	cd crates\nanovms-core && $(GO) vet ./...

go-test:
	cd crates\nanovms-core && $(GO) test ./...
