#!/usr/bin/env bash
# install.sh — Herdr plugin install companion for herdr-jcode.
#
# Cross-platform companion to `herdr plugin install KooshaPari/herdr-jcode`:
# copies the wrapper + detection rule into the user's local Herdr install so
# the plugin works immediately without requiring Herdr to clone the repo first.
#
# Supported: macOS, Linux, Windows (git-bash / WSL).
# NOT supported: native Windows cmd.exe / PowerShell. The README points users
# to WSL or git-bash for Windows.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ID="${PLUGIN_ID:-kooshapari.herdr-jcode}"

HERDR_CONFIG_DIR="${HERDR_CONFIG_DIR:-$HOME/.config/herdr}"
HERDR_DATA_DIR="${HERDR_DATA_DIR:-$HOME/.local/share/herdr}"

PLUGIN_CONFIG_DIR="$HERDR_CONFIG_DIR/plugins/$PLUGIN_ID"
AGENT_DETECTION_DIR="$HERDR_CONFIG_DIR/agent-detection"

# --- preflight ---
case "$(uname -s 2>/dev/null || echo unknown)" in
  MINGW*|MSYS*|CYGWIN*) _OS="windows" ;;
  Darwin*)             _OS="macos"  ;;
  Linux*)              _OS="linux"  ;;
  *)                   _OS="unix"   ;;
esac

_log() { printf '[herdr-jcode install] %s\n' "$*" >&2; }
_die() { printf '[herdr-jcode install] ERROR: %s\n' "$*" >&2; exit 1; }

_log "Detected OS: $_OS"

if [[ ! -d "$HERDR_CONFIG_DIR" && ! -d "$HERDR_DATA_DIR" ]]; then
  _log "Herdr not initialized. Run 'herdr init' first, then re-run this script."
  _die "missing Herdr config dir (${HERDR_CONFIG_DIR}) and data dir (${HERDR_DATA_DIR})"
fi

# --- copy wrapper script ---
mkdir -p "$PLUGIN_CONFIG_DIR/bin"
cp "$SCRIPT_DIR/bin/herdr-jcode-report" "$PLUGIN_CONFIG_DIR/bin/herdr-jcode-report"
chmod +x "$PLUGIN_CONFIG_DIR/bin/herdr-jcode-report"
_log "installed wrapper: $PLUGIN_CONFIG_DIR/bin/herdr-jcode-report"

# --- copy manifest ---
cp "$SCRIPT_DIR/herdr-plugin.toml" "$PLUGIN_CONFIG_DIR/herdr-plugin.toml"
_log "installed manifest: $PLUGIN_CONFIG_DIR/herdr-plugin.toml"

# --- merge detection rules into ~/.config/herdr/agent-detection/ ---
mkdir -p "$AGENT_DETECTION_DIR"
cp "$SCRIPT_DIR/agent-detection/jcode.toml" "$AGENT_DETECTION_DIR/jcode.toml"
_log "installed detection: $AGENT_DETECTION_DIR/jcode.toml"

# --- check that jcode binary is reachable (advisory only) ---
JCODE_BIN=""
if command -v jcode >/dev/null 2>&1; then
  JCODE_BIN="$(command -v jcode)"
elif [[ "$_OS" == "windows" ]] && command -v jcode.exe >/dev/null 2>&1; then
  JCODE_BIN="$(command -v jcode.exe)"
fi

if [[ -n "$JCODE_BIN" ]]; then
  _log "found jcode binary: $JCODE_BIN"
else
  _log "warning: 'jcode' binary not on PATH. Install Jcode before starting a session."
fi

# --- restart hint ---
_log "Done. Restart Herdr or run 'herdr plugin reload' to pick up the new plugin."

cat <<EOF

Next steps:
  1. Verify the plugin is loaded:
       herdr plugin list
  2. Restart Herdr (or run 'herdr server reload-agent-manifests') so the
     detection rules in agent-detection/jcode.toml are picked up.
  3. Open a pane running 'jcode' inside Herdr — the pane should auto-detect
     as 'jcode' and start emitting pane.report_agent events.
  4. Inspect pane state:
       herdr agent list
       herdr agent explain --json

EOF

exit 0
