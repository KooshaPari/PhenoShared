#!/usr/bin/env bash
# build_nim.sh — compile the Nim FFI bindings against libpheno_qwen.dylib.
#
# Steps:
#   1. Install Nim via scripts/install_nim.sh if not present
#   2. Build the host dylib (via build_dylib.sh) when missing
#   3. Compile qwen3_5.nim, decode.nim, bench.nim, main.nim with `nim c`
#
# Outputs land in $BUILD_DIR (default: ./kernels/qwen3.5-0.8b/build):
#   - nim_qwen3_5 (test binary from qwen3_5.nim's `when isMainModule` block)
#   - nim_decode  (decode.nim CLI)
#   - nim_bench   (bench.nim CLI)
#   - nim_main    (Pony-style smoke test)
#
# Requires: nim 2.0+ (brew install nim) OR via scripts/install_nim.sh.
#
# Run:
#   DYLD_LIBRARY_PATH=../build ./nim_main

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_DIR="$(cd "$HERE/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-${KERNEL_DIR}/build}"
DYLIB="$BUILD_DIR/libpheno_qwen.dylib"
NIM_DIR="$KERNEL_DIR/nim"

log() { printf '[build_nim] %s\n' "$*"; }

# ---------------------------------------------------------------------------
# 1. Ensure Nim toolchain is present.
# ---------------------------------------------------------------------------
if ! command -v nim >/dev/null 2>&1 && [[ ! -x "${HOME}/.nimble/bin/nim" ]]; then
  log "nim not found; running install_nim.sh"
  bash "$HERE/install_nim.sh"
fi

# Source choosenim-env if it exists (no-op if already on PATH).
if [[ -f "${HOME}/.nimble/bin/choosenim-env" ]]; then
  # shellcheck disable=SC1090
  source "${HOME}/.nimble/bin/choosenim-env"
fi

if ! command -v nim >/dev/null 2>&1; then
  if [[ -x "${HOME}/.nimble/bin/nim" ]]; then
    export PATH="${HOME}/.nimble/bin:${PATH}"
  else
    echo "[build_nim] ERROR: nim still not on PATH after install_nim.sh"
    exit 1
  fi
fi

log "using nim: $(command -v nim) ($(nim --version 2>&1 | head -1))"

# ---------------------------------------------------------------------------
# 2. Build the host dylib when missing.
# ---------------------------------------------------------------------------
if [[ ! -f "$DYLIB" ]]; then
  log "libpheno_qwen.dylib missing; running build_dylib.sh first"
  bash "$HERE/build_dylib.sh" >/dev/null
fi

if [[ ! -f "$DYLIB" ]]; then
  log "WARN: libpheno_qwen.dylib still missing; nim binaries will fail at runtime"
  log "      (compile-only mode — useful for syntax validation)"
fi

# ---------------------------------------------------------------------------
# 3. Compile each Nim module.
# ---------------------------------------------------------------------------
mkdir -p "${BUILD_DIR}"

NIMFLAGS=(
  --hints:off
  --warnings:off
  --skipUserCfg
  --skipParentCfg
  --gc:arc
  --opt:speed
)

# 3a. qwen3_5.nim — the library module.  Build it standalone so its
# `when isMainModule` block (CLI test) produces a runnable binary too.
log "compiling qwen3_5.nim → nim_qwen3_5"
nim c "${NIMFLAGS[@]}" \
    --out:"${BUILD_DIR}/nim_qwen3_5" \
    --nimcache:"${BUILD_DIR}/nimcache_qwen3_5" \
    "${NIM_DIR}/qwen3_5.nim"

# 3b. decode.nim — token-by-token decode loop CLI.
log "compiling decode.nim → nim_decode"
nim c "${NIMFLAGS[@]}" \
    --out:"${BUILD_DIR}/nim_decode" \
    --nimcache:"${BUILD_DIR}/nimcache_decode" \
    "${NIM_DIR}/decode.nim"

# 3c. bench.nim — Nim-vs-C++ latency benchmark.
log "compiling bench.nim → nim_bench"
nim c "${NIMFLAGS[@]}" \
    --out:"${BUILD_DIR}/nim_bench" \
    --nimcache:"${BUILD_DIR}/nimcache_bench" \
    "${NIM_DIR}/bench.nim"

# 3d. main.nim — Pony-style smoke test (mirrors pony/main.pony).
log "compiling main.nim → nim_main"
nim c "${NIMFLAGS[@]}" \
    --out:"${BUILD_DIR}/nim_main" \
    --nimcache:"${BUILD_DIR}/nimcache_main" \
    "${NIM_DIR}/main.nim"

log "DONE."
ls -lh "${BUILD_DIR}"/nim_* 2>/dev/null || true