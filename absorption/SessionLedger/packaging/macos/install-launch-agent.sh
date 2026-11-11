#!/usr/bin/env bash
# Install the per-user SessionLedger daemon LaunchAgent.
#
# Installation is explicit (this script is never called by the app installer),
# while the daemon itself discovers supported local roots.  No transcript path
# is embedded in the plist, so adding/removing a harness does not require
# editing launchd configuration.  The service remains loopback-only.
set -euo pipefail

LABEL="${LABEL:-com.sessionledger.daemon}"
DAEMON_BINARY="${DAEMON_BINARY:-$HOME/.local/bin/sl-daemon}"
OUT_DIR="${OUT_DIR:-$HOME/.local/share/sessionledger/out}"
BIND="${BIND:-127.0.0.1:8080}"
PLIST_DIR="${PLIST_DIR:-$HOME/Library/LaunchAgents}"
PLIST_PATH="$PLIST_DIR/$LABEL.plist"
START="${START:-0}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: LaunchAgents are macOS-only (got $(uname -s))." >&2
  exit 1
fi
if [[ ! -x "$DAEMON_BINARY" ]]; then
  echo "error: daemon binary is missing or not executable: $DAEMON_BINARY" >&2
  echo "Install it first with INSTALL_DAEMON=1 packaging/macos/install-local.sh" >&2
  exit 1
fi
if [[ "$BIND" != 127.* && "$BIND" != "[::1]:"* && "$BIND" != "localhost:"* ]]; then
  echo "error: LaunchAgent bind must be loopback (got $BIND)" >&2
  exit 1
fi

mkdir -p "$PLIST_DIR" "$OUT_DIR"
tmp="$(mktemp "${PLIST_PATH}.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

# Plist values are escaped for XML; reject control characters rather than
# generating a malformed launchd job. Paths are operator-controlled env vars.
for value in "$DAEMON_BINARY" "$OUT_DIR" "$BIND"; do
  if [[ "$value" == *$'\n'* || "$value" == *$'\r'* || "$value" == *'<'* || "$value" == *'>'* || "$value" == *'&'* ]]; then
    echo "error: launchd value contains unsupported XML/control characters" >&2
    exit 1
  fi
done

cat >"$tmp" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$DAEMON_BINARY</string>
    <string>serve</string>
    <string>--out</string><string>$OUT_DIR</string>
    <string>--http-bind</string><string>$BIND</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Interactive</string>
  <key>StandardOutPath</key><string>$OUT_DIR/daemon.log</string>
  <key>StandardErrorPath</key><string>$OUT_DIR/daemon.err.log</string>
</dict>
</plist>
EOF
mv "$tmp" "$PLIST_PATH"
trap - EXIT

if [[ "$START" == "1" ]]; then
  launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$UID" "$PLIST_PATH"
  launchctl kickstart -k "gui/$UID/$LABEL"
  echo "Started $LABEL; health: sl-daemon status"
else
  echo "Installed $PLIST_PATH (not started)"
  echo "Start: START=1 $0"
fi
