#!/usr/bin/env bash
# install.sh — companion installer for the herdr-helioslite plugin.
#
# Runs the platform-appropriate setup:
#   * macOS / Linux : copy bin/ into ~/.local/bin, refresh detection rules.
#   * Windows (msys/git-bash/WSL) : same, with .exe suffix awareness.
#
# This script does NOT require herdr to already be installed — if herdr is
# absent, it prints the install command and continues so users can install
# Herdr afterwards and re-run.

set -euo pipefail

PLUGIN_NAME="herdr-helioslite"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '[%s-install] %s\n' "$PLUGIN_NAME" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- detect host ------------------------------------------------------------

os="$(uname -s 2>/dev/null || echo unknown)"
case "$os" in
  Darwin)            target_os="macos" ;;
  Linux)             target_os="linux" ;;
  MINGW*|MSYS*|CYGWIN*) target_os="windows" ;;
  *)                 target_os="linux" ;;  # default to POSIX shell
esac
log "detected host: $target_os ($os)"

# ---- resolve dest -----------------------------------------------------------

if [[ -n "${HERDR_HOME:-}" ]]; then
  plugin_root="$HERDR_HOME"
elif [[ "$target_os" == "windows" ]]; then
  plugin_root="${HERDR_HOME:-${USERPROFILE:-$HOME}/.config/herdr}"
else
  plugin_root="${HERDR_HOME:-$HOME/.config/herdr}"
fi
dest="${plugin_root}/plugins/local/${PLUGIN_NAME}"
log "install destination: $dest"

mkdir -p "$dest/bin" "$dest/agent-detection" "$dest/docs"

cp -f "$SCRIPT_DIR/herdr-plugin.toml"   "$dest/herdr-plugin.toml"
cp -f "$SCRIPT_DIR/bin/herdr-helioslite-report" "$dest/bin/herdr-helioslite-report"
cp -f "$SCRIPT_DIR/agent-detection/helioslite.toml" "$dest/agent-detection/helioslite.toml"
cp -f "$SCRIPT_DIR/docs/HERDR_VS_ACP.md" "$dest/docs/HERDR_VS_ACP.md"
cp -f "$SCRIPT_DIR/README.md"           "$dest/README.md"
chmod +x "$dest/bin/herdr-helioslite-report"

# ---- register detection rules globally --------------------------------------

detect_dir="${plugin_root}/agent-detection"
mkdir -p "$detect_dir"
cp -f "$SCRIPT_DIR/agent-detection/helioslite.toml" "$detect_dir/helioslite.toml"
log "detection rules installed at $detect_dir/helioslite.toml"

# ---- symlink entrypoint into ~/.local/bin -----------------------------------

if [[ -n "${HOME:-}" ]]; then
  bin_dir="$HOME/.local/bin"
  mkdir -p "$bin_dir"
  ln -sf "$dest/bin/herdr-helioslite-report" "$bin_dir/herdr-helioslite-report"
  log "symlinked entrypoint at $bin_dir/herdr-helioslite-report"
fi

# ---- optional: refresh herdr -------------------------------------------------

if command -v herdr >/dev/null 2>&1; then
  if herdr plugin install "local://${PLUGIN_NAME}" 2>/dev/null; then
    log "herdr plugin install: ok"
  else
    log "herdr plugin install failed — run \`herdr plugin install ${PLUGIN_NAME}\` manually"
  fi
else
  log "herdr CLI not found on PATH — install Herdr and run:"
  log "    herdr plugin install ${PLUGIN_NAME}"
fi

# ---- HeliosLite advisory ----------------------------------------------------

if ! command -v helioslite >/dev/null 2>&1; then
  log "helioslite binary not found on PATH — plugin will idle until installed."
  log "Install HeliosLite: https://github.com/KooshaPari/HeliosLite"
fi

log "install complete."
