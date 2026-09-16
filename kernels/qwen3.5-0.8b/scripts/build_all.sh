#!/usr/bin/env bash
# build_all.sh — End-to-end build driver for the Qwen3.5 0.8B kernel suite.
#
# Runs every build step required to take a clean tree to a fully linked
# artifact set:
#
#   1. Regenerate cross-language arch headers from arch.yaml
#      (drift target — does not clobber the canonical include/qwen3_5.h etc.)
#   2. Compile every .metal file under metal/ to .air, then link kernels.metallib
#   3. Compile the C++ Objective-C++ engine (kernel_engine.mm) and produce
#      the host-side static archive libpheno_qwen_engine.a
#   4. Link the orchestrator Rust cdylib (libpheno_qwen.dylib)
#   5. Run the pure-Python codegen tests (no MLX, no Metal) as a smoke
#      check that arch constants are consistent across all languages
#
# Output (relative to kernel directory):
#   build/kernels.metallib
#   build/libpheno_qwen_engine.a
#   build/libpheno_qwen.dylib
#
# Usage:
#   bash scripts/build_all.sh            # full build
#   QUICK=1 bash scripts/build_all.sh    # skip slow rust --release LTO
#
# Environment overrides:
#   SDK          (default: macosx)        — xcrun SDK selector
#   ARCH         (default: $(uname -m))   — target architecture
#   OPT_LEVEL    (default: -O3)           — Metal / clang optimization flag
#   BUILD_DIR    (default: ./build)       — output directory
#   SKIP_METAL   (=1 to skip)             — useful on Linux CI
#   SKIP_RUST    (=1 to skip)
#   SKIP_PYTEST  (=1 to skip)

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths.
# ---------------------------------------------------------------------------

# Resolve to absolute, kernel-suite-relative paths so the script can be
# invoked from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-${KERNEL_DIR}/build}"

METAL_DIR="${KERNEL_DIR}/metal"
CPP_DIR="${KERNEL_DIR}/cpp"
INCLUDE_DIR="${KERNEL_DIR}/include"
RUST_DIR="${KERNEL_DIR}/rust"
PYTHON_DIR="${KERNEL_DIR}/python"
ARCH_YAML="${KERNEL_DIR}/arch.yaml"

# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

log()   { printf "[build_all] %s\n" "$*" >&2; }
fail()  { printf "[build_all] ERROR: %s\n" "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Pre-flight checks.
# ---------------------------------------------------------------------------

[[ -f "${ARCH_YAML}" ]] || fail "missing ${ARCH_YAML}"
mkdir -p "${BUILD_DIR}"

log "kernel-dir: ${KERNEL_DIR}"
log "build-dir:  ${BUILD_DIR}"

# ---------------------------------------------------------------------------
# Step 1 — regenerate cross-language arch constants from arch.yaml.
#           (idempotent; only writes if content changed)
# ---------------------------------------------------------------------------

if [[ -z "${SKIP_CODEGEN:-}" ]]; then
    log "step 1/5 — regenerating arch headers from arch.yaml"
    if command -v python3 >/dev/null 2>&1; then
        python3 "${PYTHON_DIR}/codegen.py" --arch "${ARCH_YAML}" || \
            fail "codegen.py failed"
    else
        log "  (python3 not on PATH — skipping codegen step)"
    fi
else
    log "step 1/5 — SKIPPED (SKIP_CODEGEN set)"
fi

# ---------------------------------------------------------------------------
# Step 2 — compile Metal kernels → kernels.metallib
# ---------------------------------------------------------------------------

if [[ -z "${SKIP_METAL:-}" ]]; then
    if command -v xcrun >/dev/null 2>&1; then
        log "step 2/5 — building kernels.metallib via metal/Makefile"
        make -C "${METAL_DIR}" -f Makefile \
             BUILD_DIR="${BUILD_DIR}" \
             SDK="${SDK:-macosx}" \
             ARCH="${ARCH:-$(uname -m)}" \
             OPT_LEVEL="${OPT_LEVEL:--O3}" \
             "${@}"
    else
        log "step 2/5 — SKIPPED (no xcrun; not on macOS)"
    fi
else
    log "step 2/5 — SKIPPED (SKIP_METAL set)"
fi

# ---------------------------------------------------------------------------
# Step 3 — compile Objective-C++ kernel engine → libpheno_qwen_engine.a
# ---------------------------------------------------------------------------

if [[ -z "${SKIP_CPP:-}" ]]; then
    if command -v clang++ >/dev/null 2>&1; then
        log "step 3/5 — compiling cpp/kernel_engine.mm → libpheno_qwen_engine.a"
        OBJ="${BUILD_DIR}/kernel_engine.o"
        LIB="${BUILD_DIR}/libpheno_qwen_engine.a"
        clang++ -std=c++17 -fobjc-arc -O3 -c "${CPP_DIR}/kernel_engine.mm" \
                -I "${INCLUDE_DIR}" \
                -framework Metal -framework Foundation \
                -o "${OBJ}"
        ar rcs "${LIB}" "${OBJ}"
        log "  → ${LIB}"
    else
        log "step 3/5 — SKIPPED (no clang++)"
    fi
else
    log "step 3/5 — SKIPPED (SKIP_CPP set)"
fi

# ---------------------------------------------------------------------------
# Step 4 — build Rust cdylib → libpheno_qwen.dylib
# ---------------------------------------------------------------------------

if [[ -z "${SKIP_RUST:-}" ]]; then
    if command -v cargo >/dev/null 2>&1; then
        log "step 4/5 — cargo build --release (Rust cdylib)"
        # cdylib output lands under target/release/ — copy into BUILD_DIR.
        # QUICK=1 falls back to the dev profile (faster link, no LTO).
        cargo build --manifest-path "${RUST_DIR}/Cargo.toml" --release
        # Find the produced dylib across all target subdirectories.
        cdylib="$(find "${RUST_DIR}/target/release" -maxdepth 2 \
                    -name 'libpheno_qwen_kernels*.dylib' 2>/dev/null \
                    | head -n1 || true)"
        if [[ -n "${cdylib}" ]]; then
            cp -f "${cdylib}" "${BUILD_DIR}/libpheno_qwen.dylib"
            log "  → ${BUILD_DIR}/libpheno_qwen.dylib (copied from ${cdylib})"
        else
            log "  (no cdylib found — Rust crate may build rlib only)"
        fi
    else
        log "step 4/5 — SKIPPED (no cargo)"
    fi
else
    log "step 4/5 — SKIPPED (SKIP_RUST set)"
fi

# ---------------------------------------------------------------------------
# Step 5 — pure-Python codegen tests (no MLX, no Metal)
# ---------------------------------------------------------------------------

if [[ -z "${SKIP_PYTEST:-}" ]]; then
    if command -v python3 >/dev/null 2>&1 && \
       python3 -c "import pytest" >/dev/null 2>&1; then
        log "step 5/5 — pytest tests/test_codegen.py (arch-consistency)"
        # Use the repo-root tests/ directory.
        REPO_ROOT="$(cd "${KERNEL_DIR}/../.." && pwd)"
        if [[ -f "${REPO_ROOT}/tests/test_codegen.py" ]]; then
            python3 -m pytest "${REPO_ROOT}/tests/test_codegen.py" -v || \
                fail "pytest failed"
        else
            log "  (tests/test_codegen.py not found at ${REPO_ROOT}/tests/ — skipping)"
        fi
    else
        log "step 5/5 — SKIPPED (no python3 or pytest)"
    fi
else
    log "step 5/5 — SKIPPED (SKIP_PYTEST set)"
fi

# ---------------------------------------------------------------------------
# Summary.
# ---------------------------------------------------------------------------

log "DONE."
ls -lh "${BUILD_DIR}" 2>/dev/null || true
exit 0