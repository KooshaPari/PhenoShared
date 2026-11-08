#!/bin/bash
# build_for_profiling.sh - Build with profiling symbols

set -e

PROJECT="${1:-.}"

echo "=== Building $PROJECT with profiling symbols ==="

# Linux - force frame pointers
if [[ "$(uname)" == "Linux" ]]; then
    export RUSTFLAGS="-C force-frame-pointers=yes -C opt-level=3"
fi

# macOS - disable stack unwinding optimizations  
if [[ "$(uname)" == "Darwin" ]]; then
    export RUSTFLAGS="-C opt-level=3"
fi

# Build release
echo "Building with: $RUSTFLAGS"
cargo build --release --bin thegent

echo ""
echo "=== Build complete ==="
echo "Run profiler with:"
echo "  ./profiler/bin/profiler.sh thegent full"
