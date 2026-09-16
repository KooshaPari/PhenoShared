#!/usr/bin/env bash
# install_nim.sh — install the Nim toolchain via choosenim on macOS.
#
# Scope:
#   - macOS preferred (this script uses the choosenim installer, which
#     also supports Linux). On non-macOS hosts we exit 0 with a note, so
#     the polyglot bootstrap stays uniform.
#   - Idempotent: skip when `nim` is already on PATH or under
#     ~/.nimble/bin or ~/.choosenim/toolchains.
#
# Usage:
#   bash kernels/qwen3.5-0.8b/scripts/install_nim.sh
#
# Exit: 0 on success or skipped; non-zero only on real install failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '[install_nim] %s\n' "$*"; }

# ---------------------------------------------------------------------------
# 1. Platform gate (soft — choosenim is cross-platform, but we follow the
#    macOS-first directive from the polyglot spec).
# ---------------------------------------------------------------------------
if [[ "$(uname -s)" != "Darwin" ]]; then
  log "choosenim-based install is macOS-first; skipping on $(uname -s)"
  log "(Linux users: curl https://nim-lang.org/choosenim/init.sh -sSf | sh -s -- -y)"
  exit 0
fi

# ---------------------------------------------------------------------------
# 2. Idempotency check.
# ---------------------------------------------------------------------------
find_nim() {
  # Look in the most common locations, in priority order.
  if command -v nim >/dev/null 2>&1; then
    command -v nim
    return 0
  fi
  if [[ -x "${HOME}/.nimble/bin/nim" ]]; then
    echo "${HOME}/.nimble/bin/nim"
    return 0
  fi
  if [[ -x "${HOME}/.choosenim/toolchains/nim/bin/nim" ]]; then
    echo "${HOME}/.choosenim/toolchains/nim/bin/nim"
    return 0
  fi
  if [[ -x "/opt/homebrew/bin/nim" ]]; then
    echo "/opt/homebrew/bin/nim"
    return 0
  fi
  return 1
}

if NIM_BIN="$(find_nim)"; then
  log "nim already installed at: ${NIM_BIN}"
  "${NIM_BIN}" --version 2>&1 | head -3 || true
  # Best-effort nimble refresh — not fatal.
  if command -v nimble >/dev/null 2>&1; then
    nimble --version 2>&1 | head -1 || true
  fi
  exit 0
fi

# ---------------------------------------------------------------------------
# 3. Real install: choosenim bootstrap.
# ---------------------------------------------------------------------------
log "downloading choosenim installer (https://nim-lang.org/choosenim/init.sh)..."
TMP_INIT="$(mktemp -t choosenim-init.XXXXXX.sh)"
trap 'rm -f "${TMP_INIT}"' EXIT

if ! curl -fsSL https://nim-lang.org/choosenim/init.sh -o "${TMP_INIT}"; then
  log "ERROR: failed to download choosenim init script"
  exit 1
fi

if ! sh "${TMP_INIT}" -y; then
  log "ERROR: choosenim init failed"
  exit 1
fi

# ---------------------------------------------------------------------------
# 4. PATH update — choosenim writes to ~/.nimble/bin/choosenim-env.
# ---------------------------------------------------------------------------
CHOOSENIM_ENV="${HOME}/.nimble/bin/choosenim-env"
if [[ -f "${CHOOSENIM_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${CHOOSENIM_ENV}"
  log "sourced ${CHOOSENIM_ENV}"
else
  # Fallback: prepend the canonical nimble bin to PATH for this process.
  export PATH="${HOME}/.nimble/bin:${PATH}"
  log "warn: ${CHOOSENIM_ENV} not found; using PATH fallback"
fi

# ---------------------------------------------------------------------------
# 5. Verify.
# ---------------------------------------------------------------------------
log "verifying install..."
if ! NIM_BIN="$(find_nim)"; then
  log "ERROR: nim binary not found after choosenim install"
  exit 1
fi

log "nim binary: ${NIM_BIN}"
"${NIM_BIN}" --version 2>&1 | head -3 || true

if command -v nimble >/dev/null 2>&1; then
  log "nimble binary: $(command -v nimble)"
  # Best-effort nimble package refresh; not fatal if it fails offline.
  nimble install --accept 2>&1 | head -5 || true
else
  log "warn: nimble not on PATH after install"
fi

log "success"