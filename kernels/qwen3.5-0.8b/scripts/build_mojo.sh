#!/usr/bin/env bash
# build_mojo.sh — compile the Mojo polyglot kernels for Qwen3.5 0.8B.
#
# Scope (this script's contract):
#   - Builds the SCOPE files (per task spec) into standalone executables
#     under build/ that can be smoke-tested directly:
#         kernels/qwen3.5-0.8b/mojo/argmax_sample.mojo → build/qwen3_5_argmax_sample
#         kernels/qwen3.5-0.8b/mojo/attn_decode.mojo    → build/qwen3_5_attn_decode
#     These two files are the deliverable from the Mojo 0.26 migration.
#   - Optionally tries `mojo package` on the whole mojo/ directory to
#     produce build/qwen3_5_kernels.mojopkg.  This step is best-effort:
#     several other files in the package (rmsnorm, rope, swiglu, main) still
#     carry pre-0.26 GPU-only primitives (stack_allocation, barrier,
#     StaticTuple, AddressSpace.SHARED, LayoutTensor) and are NOT in scope
#     for this commit.  The package build is therefore reported but not
#     allowed to fail the script; per-file checks succeed regardless.
#   - macOS-arm64 only (Apple GPU + Metal).  Other hosts exit 0 cleanly.
#   - Idempotent: up-to-date binaries are skipped.
#
# Outputs (under build/, default = kernels/qwen3.5-0.8b/build):
#   qwen3_5_argmax_sample   — smoke binary for argmax_sample.mojo
#   qwen3_5_attn_decode     — smoke binary for attn_decode.mojo
#   qwen3_5_kernels.mojopkg — best-effort package bundle (may be absent)
#
# Usage:
#   bash scripts/build_mojo.sh                  # default build
#   BUILD_DIR=/tmp/pheno bash scripts/build_mojo.sh
#   FORCE=1 bash scripts/build_mojo.sh          # ignore up-to-date check
#
# Prerequisites: install_mojo.sh must have produced a working `mojo` binary.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MOJO_DIR="${KERNEL_DIR}/mojo"
BUILD_DIR="${BUILD_DIR:-${KERNEL_DIR}/build}"
MOJOPKG="${BUILD_DIR}/qwen3_5_kernels.mojopkg"

# SCOPE: the two kernels this commit migrates, plus types.mojo (read-only).
# Each SCOPE source is a self-contained .mojo with its own `fn main()` so it
# can be compiled as a standalone executable via `mojo build <file> -o bin`.
SCOPE_SOURCES=(
  "${MOJO_DIR}/argmax_sample.mojo"
  "${MOJO_DIR}/attn_decode.mojo"
)

log()  { printf "[build_mojo] %s\n" "$*" >&2; }
warn() { printf "[build_mojo] WARN: %s\n" "$*" >&2; }
fail() { printf "[build_mojo] ERROR: %s\n" "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Locate the Mojo toolchain.
# ---------------------------------------------------------------------------
find_mojo() {
  if command -v mojo >/dev/null 2>&1; then
    command -v mojo
    return 0
  fi
  if [[ -x "${HOME}/.local/bin/mojo" ]]; then
    printf '%s\n' "${HOME}/.local/bin/mojo"
    return 0
  fi
  return 1
}

if ! MOJO_BIN="$(find_mojo)"; then
  log "mojo binary not found on PATH or in ~/.local/bin"
  log "run: bash ${SCRIPT_DIR}/install_mojo.sh"
  log "(skipping mojo build; metal/cpp/rust/nim remain buildable independently)"
  exit 0
fi
log "mojo: ${MOJO_BIN}"
"${MOJO_BIN}" --version 2>&1 | head -1 || true

# ---------------------------------------------------------------------------
# 2. Platform gate.
# ---------------------------------------------------------------------------
UNAME_S="$(uname -s)"
UNAME_M="$(uname -m)"
if [[ "${UNAME_S}:${UNAME_M}" != "Darwin:arm64" ]]; then
  log "Mojo polyglot kernels target Apple GPU; skipping on ${UNAME_S}/${UNAME_M}"
  log "(sources remain usable on other hosts for review; no binary build attempted)"
  exit 0
fi

# ---------------------------------------------------------------------------
# 3. Pre-flight checks on the source tree.
# ---------------------------------------------------------------------------
[[ -d "${MOJO_DIR}" ]] || fail "missing mojo source dir: ${MOJO_DIR}"
mkdir -p "${BUILD_DIR}"

log "scope files (in this commit):"
for f in "${SCOPE_SOURCES[@]}"; do
  if [[ ! -f "${f}" ]]; then
    fail "missing scope source: ${f}"
  fi
  log "  ok: ${f#${KERNEL_DIR}/}"
done

# ---------------------------------------------------------------------------
# 4. Build each SCOPE source as a standalone executable.
# ---------------------------------------------------------------------------
# Each SCOPE file is self-contained (no relative imports of qwen3_5_types)
# so it can be built via `mojo build <file>.mojo -o build/<bin>` directly.
# This avoids the package-level failure that occurs when the un-migrated
# files in the same directory (rmsnorm, rope, swiglu, main) are pulled into
# `mojo package`.  Each binary is a self-test driver that exercises its
# kernel on tiny synthetic inputs.
build_standalone() {
  local src="$1"
  local base
  base="$(basename "${src}" .mojo)"
  local bin="${BUILD_DIR}/qwen3_5_${base}"

  if [[ "${FORCE:-0}" != "1" && -x "${bin}" && "${src}" -nt "${bin}" ]]; then
    log "skipping (up to date): $(basename "${bin}")"
    return 0
  fi
  log "compiling $(basename "${src}") -> $(basename "${bin}")"
  if ! "${MOJO_BIN}" build "${src}" -o "${bin}" 2>&1 \
        | sed 's/^/[mojo] /' >&2; then
    fail "mojo build failed for ${src}"
  fi
  log "  ok: ${bin}"
}

for src in "${SCOPE_SOURCES[@]}"; do
  build_standalone "${src}"
done

# ---------------------------------------------------------------------------
# 5. Best-effort package build (informational only).
# ---------------------------------------------------------------------------
# The .mojopkg directory bundles every file in mojo/ into an importable
# artifact for downstream consumers (Mojo CLI driver, higher-level
# harnesses, etc.).  Several non-scope files still use pre-0.26 GPU
# primitives; the package build is therefore reported but not allowed to
# fail the overall script.  The standalone binaries built in step 4 are
# the authoritative deliverable.
log "best-effort package build (informational; non-scope files may fail):"
if [[ "${FORCE:-0}" != "1" && -d "${MOJOPKG}" ]]; then
  needs_pkg=0
  while IFS= read -r src; do
    if [[ "${src}" -nt "${MOJOPKG}" ]]; then
      needs_pkg=1
      break
    fi
  done < <(find "${MOJO_DIR}" -name '*.mojo' -print)
  if [[ "${needs_pkg}" -eq 0 ]]; then
    log "  mojopkg up to date: ${MOJOPKG}"
  else
    rm -rf "${MOJOPKG}"
    if "${MOJO_BIN}" package "${MOJO_DIR}" -o "${MOJOPKG}" 2>&1 \
         | sed 's/^/[mojo] /' >&2; then
      log "  ok: ${MOJOPKG}"
    else
      warn "  mojo package build did not succeed — non-scope files still"
      warn "  carry pre-0.26 GPU primitives.  See commit message."
      warn "  Standalone SCOPE binaries above are unaffected."
    fi
  fi
else
  rm -rf "${MOJOPKG}"
  if "${MOJO_BIN}" package "${MOJO_DIR}" -o "${MOJOPKG}" 2>&1 \
       | sed 's/^/[mojo] /' >&2; then
    log "  ok: ${MOJOPKG}"
  else
    warn "  mojo package build did not succeed — non-scope files still"
    warn "  carry pre-0.26 GPU primitives.  See commit message."
    warn "  Standalone SCOPE binaries above are unaffected."
  fi
fi

# ---------------------------------------------------------------------------
# 6. Summary.
# ---------------------------------------------------------------------------
log "DONE."
ls -lh "${BUILD_DIR}"/qwen3_5_argmax_sample "${BUILD_DIR}"/qwen3_5_attn_decode 2>/dev/null || true

cat <<NEXT

[build_mojo] SUCCESS — Mojo 0.26 SCOPE files compiled.

Quick smoke tests:
    ${BUILD_DIR}/qwen3_5_argmax_sample
    ${BUILD_DIR}/qwen3_5_attn_decode

Or run the full smoke-test suite:
    bash ${SCRIPT_DIR}/test_mojo.sh

NEXT