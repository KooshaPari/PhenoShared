.PHONY: build test lint clean

# Quillr HTTP toolkit

build:
	cargo build --release

test:
	cargo test

lint:
	cargo clippy -- -D warnings
	cargo fmt --check

clean:
	cargo clean
