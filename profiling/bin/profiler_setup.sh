#!/bin/bash
# profiler_setup.sh - Install all profiling tools

set -e

echo "=== Installing Rust Profilers ==="

# Check if cargo is installed
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
    source ~/.cargo/env
fi

echo "Installing profiling tools..."

# CPU profiling
cargo install cargo-flamegraph --locked 2>/dev/null || cargo install cargo-flamegraph
cargo install samply --locked 2>/dev/null || cargo install samply

# Memory profiling  
cargo install dhat-rs --locked 2>/dev/null || cargo install dhat-rs
cargo install heaptrack --locked 2>/dev/null || cargo install heaptrack

# Benchmarking
cargo install criterion --locked 2>/dev/null || cargo install criterion

# For thegent or your codebase
cargo install cargo-bloat --locked 2>/dev/null || cargo install cargo-bloat
cargo install cargo-llvm-cov --locked 2>/dev/null || cargo install cargo-llvm-cov

echo ""
echo "=== Verifying installations ==="
cargo flamegraph --version 2>/dev/null && echo "✓ cargo-flamegraph"
samply --version 2>/dev/null && echo "✓ samply"
dhat --version 2>/dev/null && echo "✓ dhat-rs"
criterion --version 2>/dev/null && echo "✓ criterion"
cargo bloat --version 2>/dev/null && echo "✓ cargo-bloat"

echo ""
echo "=== Profiler setup complete ==="
echo "Run 'profiler.sh' to profile Codex or your codebase"
