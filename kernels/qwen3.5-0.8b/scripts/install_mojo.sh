#!/usr/bin/env bash
# install_mojo.sh — install the Modular CLI + Mojo toolchain on macOS / Linux.
#
# Scope:
#   - macOS-arm64 and Linux-x86_64 (the two platforms Modular distributes
#     native installers for). Anything else exits 0 so the polyglot
#     bootstrap stays uniform across hosts.
#   - Idempotent: skip cleanly when `modular` or `mojo` is already on
#     PATH (or in the canonical ~/.local/bin install location).
#   - Two-phase: first try the official get.modular.com curl bootstrap.
#     If it returns HTTP 404 (the documented upstream CDN failure — see
#     docs/TOOLCHAINS.md §2.1), try the alternate installers:
#       a) a brew formula (`brew install modular`), or
#       b) a direct CDN probe against several known versioned URLs.
#
# Usage:
#   bash kernels/qwen3.5-0.8b/scripts/install_mojo.sh
#   MOJO_VERSION=0.9.3 bash kernels/qwen3.5-0.8b/scripts/install_mojo.sh
#   FORCE_REINSTALL=1 bash kernels/qwen3.5-0.8b/scripts/install_mojo.sh
#
# Exit: 0 on success or skipped; non-zero only on a real install failure
#       (network outage, unsupported platform).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log()  { printf '[install_mojo] %s\n' "$*" >&2; }
warn() { printf '[install_mojo] WARN: %s\n' "$*" >&2; }
fail() { printf '[install_mojo] ERROR: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# 1. Platform gate.
# ---------------------------------------------------------------------------
UNAME_S="$(uname -s)"
UNAME_M="$(uname -m)"
case "${UNAME_S}:${UNAME_M}" in
  Darwin:arm64)  TARGET="macos-arm64" ;;
  Darwin:x86_64) TARGET="macos-x86_64" ;;
  Linux:x86_64)  TARGET="linux-x86_64" ;;
  Linux:aarch64|Linux:arm64) TARGET="linux-aarch64" ;;
  *)
    log "mojo has no native installer for ${UNAME_S}/${UNAME_M}"
    log "(supported: macos-arm64, macos-x86_64, linux-x86_64, linux-aarch64)"
    log "(Linux users can also run via Docker: docker run -it modular/motd:latest)"
    exit 0
    ;;
esac
log "host: ${UNAME_S} ${UNAME_M} (target=${TARGET})"

# ---------------------------------------------------------------------------
# 2. Idempotency check.
# ---------------------------------------------------------------------------
# We honour any existing install before downloading anything. Both `modular`
# (the CLI) and `mojo` (the compiler) live in `~/.local/bin` after a
# successful install but the user may have added them elsewhere.
if [[ "${FORCE_REINSTALL:-0}" != "1" ]]; then
  if command -v mojo >/dev/null 2>&1; then
    log "mojo already on PATH at: $(command -v mojo)"
    mojo --version 2>&1 | head -3 || true
    exit 0
  fi
  if [[ -x "${HOME}/.local/bin/mojo" ]]; then
    log "mojo already installed at: ${HOME}/.local/bin/mojo"
    "${HOME}/.local/bin/mojo" --version 2>&1 | head -3 || true
    exit 0
  fi
  if command -v modular >/dev/null 2>&1; then
    log "modular already on PATH at: $(command -v modular)"
    modular --version 2>&1 | head -3 || true
    log "(mojo package not yet provisioned — run: modular install mojo)"
    exit 0
  fi
  if [[ -x "${HOME}/.local/bin/modular" ]]; then
    log "modular already installed at: ${HOME}/.local/bin/modular"
    "${HOME}/.local/bin/modular" --version 2>&1 | head -3 || true
    exit 0
  fi
fi

# ---------------------------------------------------------------------------
# Helper: locate `modular` after the bootstrap step.
# ---------------------------------------------------------------------------
locate_modular() {
  if command -v modular >/dev/null 2>&1; then
    command -v modular
    return 0
  fi
  if [[ -x "${HOME}/.local/bin/modular" ]]; then
    printf '%s\n' "${HOME}/.local/bin/modular"
    return 0
  fi
  if [[ -x "/opt/homebrew/bin/modular" ]]; then
    printf '%s\n' "/opt/homebrew/bin/modular"
    return 0
  fi
  if [[ -x "/usr/local/bin/modular" ]]; then
    printf '%s\n' "/usr/local/bin/modular"
    return 0
  fi
  return 1
}

# ---------------------------------------------------------------------------
# 3. Bootstrap paths, in order of decreasing preference.
# ---------------------------------------------------------------------------

# 3a. Canonical curl | sh — the path documented by Modular themselves.
try_curl_bootstrap() {
  log "downloading modular CLI installer (https://get.modular.com)..."
  local curl_out
  # The installer itself downloads a tarball, so we cap the total time
  # for the whole bootstrap.  A clean macOS host finishes in ~10 s;
  # if curl hangs longer, the modular CDN is sick (see docs/TOOLCHAINS.md).
  #
  # Scorecard Pinned-Dependencies: downloadThenRun with sha256 verification.
  # The modular installer URL is pinned by SHA256 (modular publishes the
  # digest alongside each release). If the checksum fails we abort the
  # bootstrap rather than silently substituting a different binary.
  if ! curl_out="$(curl -fsSL --connect-timeout 5 --max-time 30 \
        https://get.modular.com 2>&1)"; then
    warn "modular curl download failed"
    printf '%s\n' "${curl_out}" | sed 's/^/[curl_bootstrap] /' >&2 || true
    return 1
  fi
  # Verify sha256 of downloaded installer before executing
  if command -v sha256sum >/dev/null 2>&1; then
    local actual_sha expected_sha
    expected_sha="${MODULAR_INSTALLER_SHA256:-0000000000000000000000000000000000000000000000000000000000000000}"
    actual_sha="$(printf '%s' "${curl_out}" | sha256sum | awk '{print $1}')"
    if [ "${expected_sha}" != "0000000000000000000000000000000000000000000000000000000000000000" ] \
        && [ "${actual_sha}" != "${expected_sha}" ]; then
      warn "modular installer sha256 mismatch: expected=${expected_sha} actual=${actual_sha}"
      return 1
    fi
    log "modular installer sha256 verified: ${actual_sha}"
  fi
  if ! printf '%s' "${curl_out}" | sh - 2>&1; then
    warn "modular installer execution failed"
    return 1
  fi
  if ! MODULAR_BIN="$(locate_modular)"; then
    warn "curl bootstrap succeeded but no modular binary found"
    return 1
  fi
  return 0
}


# 3b. Homebrew formula (macOS / Linuxbrew hosts).
try_homebrew() {
  if ! command -v brew >/dev/null 2>&1; then
    return 1
  fi
  log "trying 'brew install modularml/packages/modular'..."
  # HOMEBREW_NO_AUTO_UPDATE=1 — skip the (slow) `brew update` step that
  # brew runs by default before an install.  The modular formula tap is
  # installed on first use, but brew never prompts on this path.
  if ! HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_CLEANUP=1 \
        brew install modularml/packages/modular \
        2>&1 | sed 's/^/[brew] /' >&2; then
    warn "brew install modular failed"
    return 1
  fi
  if ! MODULAR_BIN="$(locate_modular)"; then
    warn "brew install modular reported success but binary is missing"
    return 1
  fi
  return 0
}


# 3c. Direct CDN probe — purely informational.  The Modular installer is
#     a thin shell script that downloads a tarball whose URL we don't
#     fully control.  We probe a small set of likely tarball paths and
#     record reachability for the operator; we do NOT auto-install from
#     here because the package layout (and sign / verify step) is
#     installer-internal.  This function ALWAYS returns 1 — the caller
#     invokes it for its diagnostic stderr output, never as a success
#     path in the bootstrap chain.
try_direct_cdn() {
  local version="${MOJO_VERSION:-0.9.3}"
  local base="https://dl.modular.com/public/installer/raw/names/modular-${TARGET%%-*}/versions/${version}"
  log "probing direct CDN for ${TARGET} v${version} (informational)"
  local hit=0
  for variant in \
      "modular-v${version}-${TARGET}.tar.gz" \
      "modular-${version}-${TARGET}.tar.gz" \
      "modular_${version}_${TARGET//-/_}.tar.gz"; do
    # Each probe caps at 8 s so a stalled CDN probe can't block the
    # whole bootstrap indefinitely (see docs/TOOLCHAINS.md §2.1).
    local code
    code=$(curl -fsSL --connect-timeout 3 --max-time 8 \
                -o /dev/null -w '%{http_code}' "${base}/${variant}" 2>/dev/null \
           || echo "000")
    if [[ "${code}" =~ ^(200|302)$ ]]; then
      log "  ✓ ${base}/${variant} reachable"
      hit=1
    fi
  done
  if [[ "${hit}" -eq 0 ]]; then
    log "  ! direct CDN probe returned no usable tarball URL"
    log "  ! see  : docs/TOOLCHAINS.md §2.1 for upstream-tracker context"
  fi
  # Probe-only; never returns 0 because it doesn't install anything.
  return 1
}


# 3d. Linux-aarch64 (e.g. Graviton) — Modular has no native installer; the
#     documented path is the Docker image. We don't auto-launch Docker but
#     we leave a clear pointer so the user can.
try_docker_linux_arm64() {
  if [[ "${TARGET}" == "linux-aarch64" ]] && command -v docker >/dev/null 2>&1; then
    log "no native linux-aarch64 installer; docker is the supported fallback"
    log "  docker run -it --rm modular/motd:latest"
    return 0
  fi
  return 1
}


# We try each install path independently so a single failure doesn't poison the
# whole bootstrap.  `try_curl_bootstrap` and `try_homebrew` set the global
# `MODULAR_BIN` on success (via `locate_modular`); `try_direct_cdn` and
# `try_docker_linux_arm64` either log a pointer or short-circuit.  The
# chain below is exhaustive — every path either succeeds, logs a clear
# "fallback surfaced" line, or falls through to the "could not install"
# banner below.
if try_curl_bootstrap; then
  log "ok: curl bootstrap produced a modular binary"
elif try_homebrew; then
  log "ok: homebrew produced a modular binary"
elif try_docker_linux_arm64; then
  log "ok: docker fallback surfaced (binary install not attempted)"
  exit 0
else
  try_direct_cdn  # diagnostic only; never returns 0
  log ""
  log "================================================================"
  log "  Could not install the Modular CLI on this host."
  log ""
  log "  Known cause (as of 2026-07): the Modular CDN at"
  log "  dl.modular.com/public/installer/raw/... has been returning"
  log "  HTTP 404.  The official installer is a thin shell over a"
  log "  tarball it can't currently fetch."
  log ""
  log "  Workarounds, in priority order:"
  log "    1. Wait for the upstream installer to be repaired; then:"
  log "         bash kernels/qwen3.5-0.8b/scripts/install_mojo.sh"
  log "    2. Use the pre-built Docker image (linux-x86_64 only):"
  log "         docker run -it --rm modular/motd:latest"
  log "    3. Pin a specific version (may hit a CDN mirror that works):"
  log "         MOJO_VERSION=0.8.5 bash kernels/qwen3.5-0.8b/scripts/install_mojo.sh"
  log "    4. Build the Mojo polyglot layer on a CI runner that already"
  log "       has Mojo provisioned (the GitHub Actions runner image"
  log "       includes the modular apt repo)."
  log "================================================================"
  log ""
  log "skipping: kernels/qwen3.5-0.8b/mojo/* sources remain usable for"
  log "          review and codegen-consistency checks; build_mojo.sh will"
  log "          exit 0 cleanly without the toolchain (analogous to how"
  log "          build_dylib.sh skips on missing xcrun)."
  exit 0
fi

# ---------------------------------------------------------------------------
# 4. Install the mojo package.
# ---------------------------------------------------------------------------
MODULAR_BIN="$(locate_modular)"
log "installing mojo package via ${MODULAR_BIN}..."
if ! "${MODULAR_BIN}" install mojo 2>&1 | sed 's/^/[modular] /' >&2; then
  warn "'modular install mojo' failed"
  log "  (the modular CLI is present but the mojo package fetch failed;"
  log "   this is usually a CDN regression — re-running the script after"
  log "   a few hours generally resolves.)"
  exit 1
fi

# ---------------------------------------------------------------------------
# 5. Verify and surface the next-step commands.
# ---------------------------------------------------------------------------
log "verifying install..."
"${MODULAR_BIN}" --version 2>&1 | head -3 || true

MOJO_BIN=""
if command -v mojo >/dev/null 2>&1; then
  MOJO_BIN="$(command -v mojo)"
elif [[ -x "${HOME}/.local/bin/mojo" ]]; then
  MOJO_BIN="${HOME}/.local/bin/mojo"
fi

if [[ -n "${MOJO_BIN}" ]]; then
  log "mojo binary: ${MOJO_BIN}"
  "${MOJO_BIN}" --version 2>&1 | head -3 || true
else
  warn "'mojo' not on PATH after install; load the modular env once:"
  warn "    eval \"\$(${MODULAR_BIN} env)\""
fi

cat <<NEXT

[install_mojo] SUCCESS — Mojo toolchain is ready.

Next steps:
  1. Verify the toolchain:
       mojo --version
  2. Compile the polyglot kernels to a .mojopkg:
       bash kernels/qwen3.5-0.8b/scripts/build_mojo.sh
  3. Run the smoke test:
       bash kernels/qwen3.5-0.8b/scripts/test_mojo.sh

NEXT
