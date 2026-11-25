#!/usr/bin/env bash
# uninstall.sh — remove herdr-forgecode plugin artifacts installed by install.sh.
#
# Does NOT remove the user's `forge` binary itself — only the Herdr-side
# wrapper, manifest, and detection rule.

set -euo pipefail

PLUGIN_ID="${PLUGIN_ID:-herdr-forgecode}"

HERDR_CONFIG_DIR="${HERDR_CONFIG_DIR:-$HOME/.config/herdr}"
AGENT_DETECTION_DIR="$HERDR_CONFIG_DIR/agent-detection"
PLUGIN_CONFIG_DIR="$HERDR_CONFIG_DIR/plugins/$PLUGIN_ID"

_log() { printf '[herdr-forgecode uninstall] %s\n' "$*" >&2; }

_log "removing plugin dir: $PLUGIN_CONFIG_DIR"
rm -rf "$PLUGIN_CONFIG_DIR" || true

rm -f "$AGENT_DETECTION_DIR/forgecode.toml" || true
_log "removed detection: $AGENT_DETECTION_DIR/forgecode.toml"

_log "Done. Restart Herdr or run 'herdr plugin reload'."

exit 0
