# Apisync Makefile
.PHONY: all build test lint format format-check doc bench clean help audit

all: lint test

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build:
	cargo build

test:
	cargo test

test-doc:
	cargo test --doc

lint:
	cargo clippy --all-targets -- -D warnings

format:
	cargo fmt

format-check:
	cargo fmt -- --check

doc:
	cargo doc --no-deps

bench:
	cargo bench

clean:
	cargo clean

audit:
	cargo audit
