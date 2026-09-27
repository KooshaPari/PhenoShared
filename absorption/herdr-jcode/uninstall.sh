#!/usr/bin/env bash
# uninstall.sh — remove herdr-jcode artifacts from the local Herdr install.
#
# Removes only this plugin's files; never touches user config or other plugins.

set -euo pipefail

PLUGIN_ID="${PLUGIN_ID:-kooshapari.herdr-jcode}"
HERDR_CONFIG_DIR="${HERDR_CONFIG_DIR:-$HOME/.config/herdr}"

PLUGIN_CONFIG_DIR="$HERDR_CONFIG_DIR/plugins/$PLUGIN_ID"
AGENT_DETECTION_DIR="$HERDR_CONFIG_DIR/agent-detection"

_log() { printf '[herdr-jcode uninstall] %s\n' "$*" >&2; }

if [[ -d "$PLUGIN_CONFIG_DIR" ]]; then
  rm -rf "$PLUGIN_CONFIG_DIR"
  _log "removed plugin dir: $PLUGIN_CONFIG_DIR"
else
  _log "plugin dir not present: $PLUGIN_CONFIG_DIR"
fi

# Only remove the detection file this plugin owns.
DETECTION_FILE="$AGENT_DETECTION_DIR/jcode.toml"
if [[ -f "$DETECTION_FILE" ]]; then
  rm -f "$DETECTION_FILE"
  _log "removed detection rule: $DETECTION_FILE"
else
  _log "detection rule not present: $DETECTION_FILE"
fi

_log "Done. Restart Herdr or run 'herdr server reload-agent-manifests' to apply."

exit 0
