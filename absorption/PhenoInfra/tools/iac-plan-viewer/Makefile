# IaC Plan Viewer — Build helpers
.PHONY: build test serve clean check

TARGET_DIR ?= target
ifdef CARGO_TARGET_DIR
TARGET_DIR = $(CARGO_TARGET_DIR)
endif

build:
	cargo build --target wasm32-unknown-unknown --release
	wasm-bindgen --target web --out-dir www/pkg $(TARGET_DIR)/wasm32-unknown-unknown/release/iac_plan_viewer.wasm

test:
	cargo test

check:
	cargo check

serve:
	python3 -m http.server 8080 --directory www 2>/dev/null || \
	python -m http.server 8080 --directory www 2>/dev/null || \
	echo "Install Python to use the dev server"

clean:
	rm -rf www/pkg target
