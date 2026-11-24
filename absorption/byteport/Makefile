.PHONY: build build-app frontend test lint clean

# BytePort multi-language platform
#
# IMPORTANT — desktop release builds:
#   `frontend/web/src-tauri` is a workspace member, so a bare
#   `cargo build --release` also compiles the GUI. Without the
#   `custom-protocol` feature that binary loads `devUrl`
#   (http://localhost:5173) instead of the embedded frontend, which
#   shows a white window whenever no Vite dev server is running
#   (WebKit error -1004). Always build the GUI via `build-app`, or via
#   `cargo build --release --features app/custom-protocol` after the
#   frontend has been compiled into `frontend/web/build`.

# Rust workspace, including a correctly-configured GUI binary.
# Requires the frontend to be built first (see `frontend`).
build: frontend
	cargo build --release --workspace --features app/custom-protocol

# Full desktop bundle (.app / .dmg / installers) via the Tauri CLI.
# The Tauri CLI enables `custom-protocol` and runs `beforeBuildCommand`
# (`npm run build`) automatically, so this is the canonical release path.
build-app:
	npm --prefix frontend/web run build
	cargo tauri build

frontend:
	npm --prefix frontend/web run build

test:
	cargo test

lint:
	cargo clippy -- -D warnings
	cargo fmt --check

clean:
	cargo clean
