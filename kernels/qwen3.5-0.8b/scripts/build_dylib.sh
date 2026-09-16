#!/usr/bin/env bash
# build_dylib.sh — Build only the host-side dynamic library (libpheno_qwen.dylib).
#
# This is the lightweight wrapper used by CI: when the Metal kernels and the
# full release profile are not needed (e.g. when validating that the
# orchestrator links and constructs an Engine), we just need the Rust cdylib
# and the C++ engine archive.
#
# Steps:
#   1. (Optional) regenerate arch headers via python/codegen.py
#   2. Compile kernel_engine.mm → libpheno_qwen_engine.a
#   3. cargo build --release → libpheno_qwen_kernels.dylib → libpheno_qwen.dylib
#
# All outputs land in $BUILD_DIR (default: ./build).
#
# Usage:
#   bash scripts/build_dylib.sh
#   BUILD_DIR=/tmp/pheno bash scripts/build_dylib.sh
#   QUICK=1 bash scripts/build_dylib.sh   # use dev profile (no LTO)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${BUILD_DIR:-${KERNEL_DIR}/build}"
CPP_DIR="${KERNEL_DIR}/cpp"
INCLUDE_DIR="${KERNEL_DIR}/include"
RUST_DIR="${KERNEL_DIR}/rust"
PYTHON_DIR="${KERNEL_DIR}/python"
ARCH_YAML="${KERNEL_DIR}/arch.yaml"

log()  { printf "[build_dylib] %s\n" "$*" >&2; }
fail() { printf "[build_dylib] ERROR: %s\n" "$*" >&2; exit 1; }

mkdir -p "${BUILD_DIR}"

# --- 1. (optional) regenerate arch headers ---------------------------------
if command -v python3 >/dev/null 2>&1 && [[ -f "${ARCH_YAML}" ]]; then
    log "regenerating arch headers"
    python3 "${PYTHON_DIR}/codegen.py" --arch "${ARCH_YAML}" || \
        fail "codegen.py failed"
fi

# --- 1b. Compile Metal kernels → kernels.metallib --------------------------
# This is the second prerequisite (alongside kernel_engine.mm) so the dylib
# can embed the metallib as a self-contained section.
if command -v xcrun >/dev/null 2>&1 && [[ -d "${KERNEL_DIR}/metal" ]]; then
    METAL_DIR="${KERNEL_DIR}/metal"
    METALLIB="${BUILD_DIR}/kernels.metallib"
    if [[ ! -f "${METALLIB}" || "${BUILD_FORCE_METAL:-0}" == "1" ]]; then
        log "compiling Metal kernels → ${METALLIB}"
        shopt -s nullglob
        AIR_FILES=()
        # Skip the kernels.metal aggregate; compile individual .metal files only.
        for src in "${METAL_DIR}"/*.metal; do
            [[ "$(basename "${src}")" == "kernels.metal" ]] && continue
            base="$(basename "${src}" .metal)"
            air="${BUILD_DIR}/${base}.air"
            xcrun -sdk macosx metal -std=metal3.0 -O3 \
                -c "${src}" -o "${air}" 2>&1 | sed "s|^|[metal/${base}] |"
            AIR_FILES+=("${air}")
        done
        shopt -u nullglob
        if (( ${#AIR_FILES[@]} > 0 )); then
            xcrun -sdk macosx metallib -o "${METALLIB}" "${AIR_FILES[@]}" \
                2>&1 | sed 's|^|[metallib] |'
            log "  → ${METALLIB} ($(du -h "${METALLIB}" | cut -f1))"
        fi
    else
        log "kernels.metallib already present ($(du -h "${METALLIB}" | cut -f1)), skipping"
    fi
fi

# --- 2. C++ engine → libpheno_qwen.dylib (the canonical dylib with C ABI) --
# This dylib exports pheno_engine_create / pheno_engine_destroy / etc.
# validate.py ctypes.CDLL()s it. It is the single source of truth.
#
# IMPORTANT: build in two steps (compile → link).  Combining compile+link in
# one invocation causes macOS's clang driver to pull in a different default
# stdlib path that doesn't include <filesystem> correctly, even though both
# flags are identical.  Splitting makes the build reliable.
if command -v xcrun >/dev/null 2>&1; then
    log "compiling kernel_engine.mm → libpheno_qwen.dylib"
    DYLIB="${BUILD_DIR}/libpheno_qwen.dylib"
    OBJ="${BUILD_DIR}/kernel_engine.o"
    METALLIB="${BUILD_DIR}/kernels.metallib"
    # Step 2a: object file
    xcrun -sdk macosx clang++ -std=c++17 -fobjc-arc -O3 -fPIC \
        -fvisibility=default \
        -I "${INCLUDE_DIR}" \
        -c "${CPP_DIR}/kernel_engine.mm" \
        -o "${OBJ}"
    # Step 2b: link into a real dylib
    xcrun -sdk macosx clang++ -dynamiclib \
        -O3 \
        -Wl,-export_dynamic \
        -Wl,-undefined,dynamic_lookup \
        -Wl,-install_name,"@rpath/libpheno_qwen.dylib" \
        -Wl,-rpath,@loader_path/ \
        -framework Metal -framework Foundation \
        -o "${DYLIB}" "${OBJ}"
    log "  → ${DYLIB}"
    # Step 2c: embed the metallib into the dylib so the dylib is self-contained
    # -sectcreate takes (segmentname, sectionname, file) — we use a fixed
    # short name (__METAL) so the linker doesn't truncate the section name.
    if [[ -f "${METALLIB}" ]]; then
        EMBED="${BUILD_DIR}/libpheno_qwen_embedded.dylib"
        xcrun -sdk macosx clang++ -dynamiclib \
            -O3 \
            -Wl,-export_dynamic \
            -Wl,-undefined,dynamic_lookup \
            -Wl,-install_name,"@rpath/libpheno_qwen.dylib" \
            -Wl,-rpath,@loader_path/ \
            -Wl,-sectcreate,__METAL,__metallib,${METALLIB} \
            -framework Metal -framework Foundation \
            -o "${EMBED}" "${OBJ}"
        cp -f "${EMBED}" "${DYLIB}"
        log "  → ${DYLIB} (with __METAL section embedded from $(basename ${METALLIB}))"
    fi
elif command -v clang++ >/dev/null 2>&1; then
    log "fallback: clang++ without xcrun (may fail on framework headers)"
    OBJ="${BUILD_DIR}/kernel_engine.o"
    DYLIB="${BUILD_DIR}/libpheno_qwen.dylib"
    clang++ -std=c++17 -fobjc-arc -O3 -fPIC \
        -fvisibility=default \
        -I "${INCLUDE_DIR}" \
        -c "${CPP_DIR}/kernel_engine.mm" \
        -o "${OBJ}"
    clang++ -dynamiclib \
        -Wl,-export_dynamic \
        -Wl,-undefined,dynamic_lookup \
        -Wl,-install_name,"@rpath/libpheno_qwen.dylib" \
        -o "${DYLIB}" "${OBJ}"
    log "  → ${DYLIB}"
else
    log "skipping C++ engine (no clang++/xcrun)"
fi

# --- 3. Rust cdylib → libpheno_qwen_kernels.dylib (kept separate) --------
# The Rust cdylib is a *secondary* artifact. validate.py uses the
# kernel_engine.mm dylib (above); the rust cdylib is consumed by Rust
# consumers wanting a higher-level API.
if command -v cargo >/dev/null 2>&1; then
    log "cargo build (release)"
    if [[ "${QUICK:-0}" == "1" ]]; then
        # Dev profile: faster link, slower runtime. Useful for CI smoke.
        cargo build --manifest-path "${RUST_DIR}/Cargo.toml"
        src_dir="${RUST_DIR}/target/debug"
    else
        cargo build --manifest-path "${RUST_DIR}/Cargo.toml" --release
        src_dir="${RUST_DIR}/target/release"
    fi
    cdylib="$(find "${src_dir}" -maxdepth 2 \
                -name 'libpheno_qwen_kernels*.dylib' 2>/dev/null \
                | head -n1 || true)"
    if [[ -n "${cdylib}" ]]; then
        cp -f "${cdylib}" "${BUILD_DIR}/libpheno_qwen_kernels.dylib"
        log "  → ${BUILD_DIR}/libpheno_qwen_kernels.dylib (copied from ${cdylib})"
    else
        log "  (no cdylib produced — crate may be rlib-only)"
    fi
else
    log "skipping Rust cdylib (no cargo)"
fi

log "DONE."
ls -lh "${BUILD_DIR}" 2>/dev/null || true
exit 0