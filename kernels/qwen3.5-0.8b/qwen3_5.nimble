# Qwen3.5 0.8B Nim bindings — installation note.
#
# The Nim toolchain is NOT currently installed in this worktree
# (`which nim` returns `not found`).  These files are present as
# documentation + a copy-pasteable example of how to consume
# `libpheno_qwen_kernels.dylib` from Nim once the toolchain is added.
#
# Install Nim (any of):
#   brew install nim                       # macOS / Linux (Homebrew)
#   curl https://nim-lang.org/download/choosenim-init.sh -sSf | sh  # cross-platform
#   apt-get install nim                     # Debian / Ubuntu
#   pacman -S nim                           # Arch
#   scoop install nim                       # Windows
#
# Build prerequisites (must run BEFORE building the Nim bindings):
#   cd ../rust && cargo build --release
#   # produces: ../rust/target/release/libpheno_qwen_kernels.dylib
#
# Build the Nim bindings:
#   nim c --hints:off --warnings:off --gc:arc --opt:speed \
#       -d:phenoCengPath="$(pwd)/../rust/target/release" \
#       --out:nim_bench bench.nim
#
# Run:
#   DYLD_LIBRARY_PATH="$(pwd)/../rust/target/release" ./nim_bench
#
# Why Nim?  Polyglot max-perf per the user's directive.  Nim compiles to
# C then to native code, with `cimport` / `dynlib` semantics that add
# literally zero FFI overhead compared to calling the C ABI from C.
# `bench.nim` measures the per-step latency and compares against the
# C++ host; the goal is to match a C-only harness to within ±5%.

version       = "0.1.0"
author        = "Phenotype"
description   = "Qwen3.5 0.8B Metal kernel engine — Nim bindings"
license       = "Apache-2.0"
srcDir        = "nim"
bin           = @["nim/bench.nim", "nim/decode.nim"]
skipDirs      = @["nim/../cpp", "nim/../rust", "nim/../zig", "nim/../metal"]

# Pure-Nim dependency: stdlib only.  cimport works on stdlib already.
requires "nim >= 1.6.0"

# The C++ engine is consumed as a pre-built dynamic library
# (`libpheno_qwen_kernels.dylib`) — see `nim/qwen3_5.nim` for the
# dynlib symbol loading.
# Pass --define:phenoCengPath="/abs/path/to/lib" to point at a custom
# location.  Default: ../rust/target/release/libpheno_qwen_kernels.dylib
const
  phenoCengPath* = "../rust/target/release"

when defined(phenoCengPath):
  const dynlibPath = phenoCengPath & "/libpheno_qwen_kernels.dylib"
else:
  const dynlibPath = "../rust/target/release/libpheno_qwen_kernels.dylib"
