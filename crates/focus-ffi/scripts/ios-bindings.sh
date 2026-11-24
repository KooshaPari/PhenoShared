#!/usr/bin/env bash
# Rust-vs-shell: this is a 3-command wrapper (cargo build + cargo run + cp-by-flag);
# writing a dedicated Rust binary to orchestrate other cargo invocations would
# be strictly worse than a 5-line bash glue. Per Phenotype scripting policy.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Workspace Cargo.lock requires edition2024 (clap_lex 1.1.0); force 1.93.1 toolchain.
CARGO="${CARGO:-cargo +1.93.1}"
$CARGO build --manifest-path "$HERE/../Cargo.toml" --release -p focus-ffi
$CARGO run --manifest-path "$HERE/../Cargo.toml" --release -p focus-ffi --bin uniffi-bindgen -- \
    generate "$HERE/../src/focus_ffi.udl" --language swift \
    --out-dir "$HERE/../../../apps/ios/FocalPoint/Sources/FocalPointCore/"
