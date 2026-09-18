#!/usr/bin/env bash
# Cross-target build guard for `phinbox`.
#
# The Windows and Linux renderers are `cfg`-gated, so a broken one is
# invisible to a native `cargo test`: it simply is never compiled. Both
# failures found in this repo were of exactly that kind — `windows.rs` had
# never compiled (a hard `format!` "unused formatting arguments" error) and
# the crate could not be checked for Windows at all because the Unix-only
# inbox IPC module was not gated.
#
# Run this after touching anything under `src/platform/`, `src/inbox/` or
# `src/installer/`. Exit status is non-zero if any checked target fails.
set -uo pipefail

crate_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
repo_root="$(cd "$crate_dir/../.." && pwd)"
cd "$repo_root" || exit 2

if ! command -v rustup >/dev/null 2>&1; then
  echo "rustup not found; cannot enumerate installed targets" >&2
  exit 2
fi

installed="$(rustup target list --installed 2>/dev/null || true)"
fail=0
checked=0

check_target() {
  local target="$1" label="$2"
  if ! printf '%s\n' "$installed" | grep -qx "$target"; then
    echo "SKIP  $label ($target) — not installed; 'rustup target add $target'"
    return
  fi
  checked=$((checked + 1))
  printf 'CHECK %s (%s) ... ' "$label" "$target"
  if cargo check -p phinbox --all-targets --target "$target" >/dev/null 2>&1; then
    echo "OK"
  else
    echo "FAILED"
    cargo check -p phinbox --all-targets --target "$target" 2>&1 | grep -E '^error' -A5 | head -40
    fail=1
  fi
}

echo "phinbox cross-target check (native: $(rustc -vV | sed -n 's/^host: //p'))"
check_target "x86_64-unknown-linux-gnu" "Linux renderer + UDS inbox"
check_target "x86_64-pc-windows-gnu"   "Windows renderer (no UDS inbox)"

if [ "$checked" -eq 0 ]; then
  echo "no cross targets installed; nothing checked" >&2
  exit 2
fi

if [ "$fail" -ne 0 ]; then
  echo "cross-target check FAILED" >&2
  exit 1
fi
echo "cross-target check passed ($checked target(s))"
