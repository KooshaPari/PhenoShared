#!/usr/bin/env bash
# build_pony.sh — compile the Pony FFI bindings against libpheno_qwen.dylib.
#
# Requires: ponyc 0.55+ (brew install ponyc).
#
# Output: ./kernels/qwen3.5-0.8b/pony/qwen3_5_kernel
#
# Run:
#   DYLD_LIBRARY_PATH=../build ./qwen3_5_kernel

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

BUILD_DIR="$ROOT/kernels/qwen3.5-0.8b/build"
DYLIB="$BUILD_DIR/libpheno_qwen.dylib"
PONY_DIR="$ROOT/kernels/qwen3.5-0.8b/pony"

if [ ! -f "$DYLIB" ]; then
    echo "[build_pony] libpheno_qwen.dylib missing; running build_dylib.sh first"
    bash "$HERE/build_dylib.sh" >/dev/null
fi

if ! command -v ponyc >/dev/null 2>&1; then
    echo "[build_pony] ponyc not found; install via: brew install ponyc"
    exit 1
fi

cd "$PONY_DIR"
ponyc -o "$PONY_DIR"
mv -f pony qwen3_5_kernel 2>/dev/null || true

echo "[build_pony] built $PONY_DIR/qwen3_5_kernel"