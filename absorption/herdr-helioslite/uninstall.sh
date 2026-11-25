#!/usr/bin/env bash
# uninstall.sh — reverse of install.sh. Removes plugin files, detaches the
# detection rule, and unlinks the entrypoint. Herdr is notified if present.

set -euo pipefail

PLUGIN_NAME="herdr-helioslite"
log() { printf '[%s-uninstall] %s\n' "$PLUGIN_NAME" "$*" >&2; }

os="$(uname -s 2>/dev/null || echo unknown)"
case "$os" in
  MINGW*|MSYS*|CYGWIN*) root="${HERDR_HOME:-${USERPROFILE:-$HOME}/.config/herdr}" ;;
  *)                    root="${HERDR_HOME:-$HOME/.config/herdr}" ;;
esac

dest="${root}/plugins/local/${PLUGIN_NAME}"
detect="${root}/agent-detection/helioslite.toml"
link="${HOME}/.local/bin/herdr-helioslite-report"

if command -v herdr >/dev/null 2>&1; then
  herdr plugin uninstall "$PLUGIN_NAME" 2>/dev/null || true
fi

[[ -L "$link" ]] && rm -f "$link"
[[ -f "$detect" ]] && rm -f "$detect"
[[ -d "$dest" ]] && rm -rf "$dest"

log "uninstall complete."
