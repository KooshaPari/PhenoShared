#!/usr/bin/env bash
# Install a locally-built SessionLedger.app for interactive dogfooding.
#
# This deliberately does not use sudo or silently install a LaunchAgent.  The
# daemon's watch root and privacy policy are operator choices; use the printed
# command (or a managed service) after installing the app.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_NAME="${APP_NAME:-SessionLedger}"
APP_SOURCE="${APP_SOURCE:-$ROOT/packaging/dist/${APP_NAME}.app}"
APP_DEST="${APP_DEST:-/Applications/${APP_NAME}.app}"
INSTALL_DAEMON="${INSTALL_DAEMON:-0}"
DAEMON_BINARY="${DAEMON_BINARY:-$ROOT/crates/sl-daemon/target/release/sl-daemon}"
DAEMON_DEST="${DAEMON_DEST:-$HOME/.local/bin/sl-daemon}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "error: this installer is macOS-only (got $(uname -s))." >&2
  exit 1
fi
if [[ ! -d "$APP_SOURCE" || ! -x "$APP_SOURCE/Contents/MacOS/$APP_NAME" ]]; then
  echo "error: app bundle is missing or invalid: $APP_SOURCE" >&2
  echo "Build it first with packaging/macos/package-app.sh or set APP_SOURCE." >&2
  exit 1
fi
command -v ditto >/dev/null || { echo "error: ditto is required." >&2; exit 1; }

mkdir -p "$(dirname "$APP_DEST")"
stage_root="$(mktemp -d "${APP_DEST}.staging.XXXXXX")"
stage_app="$stage_root/$APP_NAME.app"
backup="${APP_DEST}.previous"
had_dest=0

cleanup_stage() {
  rm -rf "$stage_root"
}
trap cleanup_stage EXIT

# Stage and validate the replacement before touching the installed bundle.
ditto "$APP_SOURCE" "$stage_app"
if [[ ! -x "$stage_app/Contents/MacOS/$APP_NAME" ]]; then
  echo "error: staged app bundle is invalid: $stage_app" >&2
  exit 1
fi

if [[ -e "$APP_DEST" ]]; then
  had_dest=1
  # Rotate the single previous archive only after the replacement is known to
  # be valid. A failed swap can therefore restore the installed app.
  rm -rf "$backup"
  ditto "$APP_DEST" "$backup"
fi

if ! rm -rf "$APP_DEST" || ! mv "$stage_app" "$APP_DEST"; then
  echo "error: failed to swap staged app into $APP_DEST" >&2
  rm -rf "$APP_DEST"
  if (( had_dest )); then
    if ! ditto "$backup" "$APP_DEST"; then
      echo "error: rollback failed; restore $backup manually" >&2
    fi
  fi
  exit 1
fi

if [[ "$INSTALL_DAEMON" == "1" ]]; then
  if [[ ! -x "$DAEMON_BINARY" ]]; then
    echo "error: daemon binary is missing or not executable: $DAEMON_BINARY" >&2
    exit 1
  fi
  mkdir -p "$(dirname "$DAEMON_DEST")"
  install -m 0755 "$DAEMON_BINARY" "$DAEMON_DEST"
fi

echo "Installed $APP_NAME.app to $APP_DEST"
if [[ "$INSTALL_DAEMON" == "1" ]]; then
  echo "Installed sl-daemon to $DAEMON_DEST"
fi
echo
echo "Start the daemon with native local-session auto-discovery:"
echo "  sl-daemon serve --out \"\$HOME/.local/share/sessionledger/out\" --http-bind 127.0.0.1:8080"
echo "For a custom transcript root, add: --watch \"\$HOME/path/to/sessions\""
echo "Then open: $APP_DEST"
