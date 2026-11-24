#!/usr/bin/env bash
# install.sh — install / uninstall / status / restart the
# com.example.agent-comms-wake launchd job for the agent-comms wake receiver.
#
# The receiver is the CONSUMER half of the agent-comms bridge. PhenoBot (the
# producer) POSTs a receipt to it over loopback and only treats a message as
# delivered when the receiver answers `200 {status:"awakened", receiptId}`.
# Without this job the receiver is not running, so every wake is refused and
# every message is retained for replay.
#
# Usage:
#   ./install.sh install    # write plist to ~/Library/LaunchAgents/ and bootstrap
#   ./install.sh uninstall  # bootout and remove the plist (keeps config/logs)
#   ./install.sh status     # READ-ONLY: show launchd state + resolved paths + log tail
#   ./install.sh restart    # bootout then bootstrap (no plist rewrite)
#
# Run from anywhere; this script resolves its own location.

set -euo pipefail

# ---------------------------------------------------------------------------
# Paths and identification (resolved up-front; cheap)
# ---------------------------------------------------------------------------

# Script dir -> agent-comms dir -> repo root.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_COMMS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${AGENT_COMMS_DIR}/.." && pwd)"
ENTRYPOINT="${AGENT_COMMS_DIR}/receiver/src/index.js"

PLIST_TEMPLATE="${SCRIPT_DIR}/com.example.agent-comms-wake.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/com.example.agent-comms-wake.plist"

LABEL="com.example.agent-comms-wake"
LAUNCHD_TARGET="gui/$(id -u)"

CONFIG_DIR="${HOME}/.config/agent-comms"
ENV_FILE="${CONFIG_DIR}/wake-receiver.env"
LOG_DIR="${CONFIG_DIR}"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Resolve node binary at install time. Do NOT trust a hardcoded /opt path: the
# live environment may use nvm, asdf, or another version manager. Use whatever
# PATH says first, falling back to /opt/homebrew/bin/node only if PATH is bare.
resolve_node() {
  local candidate
  if candidate="$(command -v node 2>/dev/null)" && [ -n "${candidate}" ]; then
    printf '%s\n' "${candidate}"
    return 0
  fi
  if [ -x "/opt/homebrew/bin/node" ]; then
    printf '%s\n' "/opt/homebrew/bin/node"
    return 0
  fi
  return 1
}

# Echo only the NAMES of variables an env-file-style line assigns (i.e.
# `NAME=...` or `export NAME=...`). NEVER prints values. Used for status output.
env_file_var_names() {
  local file="$1"
  [ -f "$file" ] || return 0
  sed -nE 's/^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)=.*/\2/p' "$file" \
    | sort -u
}

usage() {
  cat >&2 <<EOF
usage: $0 {install|uninstall|status|restart}
EOF
  exit 2
}

# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

do_install() {
  # The entrypoint MUST exist before launchd ever sees the job. The previous
  # bridge incarnation pointed at a wiped /private/tmp path and launchd
  # crash-looped 4414 times before anyone noticed; verifying here is the whole
  # point of this installer.
  if [ ! -f "$ENTRYPOINT" ]; then
    echo "ERROR: entrypoint not found: $ENTRYPOINT" >&2
    echo "       refusing to install a launchd job that would crash-loop." >&2
    exit 1
  fi

  local node_bin
  if ! node_bin="$(resolve_node)"; then
    echo "ERROR: could not resolve a node binary (need Node 20+)." >&2
    exit 1
  fi

  if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: missing $ENV_FILE" >&2
    echo "       It must define WAKE_RECEIVER_TOKEN (and may set" >&2
    echo "       WAKE_RECEIVER_PORT / WAKE_RECEIVER_STATE /" >&2
    echo "       WAKE_RECEIVER_MAP_FILE). Create it with:" >&2
    echo "         mkdir -p $CONFIG_DIR && chmod 700 $CONFIG_DIR" >&2
    echo "         printf 'WAKE_RECEIVER_TOKEN=<generated>\\n' > $ENV_FILE" >&2
    echo "         chmod 600 $ENV_FILE" >&2
    exit 1
  fi
  chmod 600 "$ENV_FILE" || true

  mkdir -p "$LOG_DIR" "$(dirname "$PLIST_DST")"

  local rendered
  rendered="$(mktemp)"
  # Substitute the placeholders. Every path is absolute; no relative resolution
  # happens under launchd, whose cwd is not the shell's.
  sed \
    -e "s|__NODE__|${node_bin}|g" \
    -e "s|__REPO__|${REPO_ROOT}|g" \
    -e "s|__ENV__|${ENV_FILE}|g" \
    -e "s|__LOG_DIR__|${LOG_DIR}|g" \
    -e "s|__HOME__|${HOME}|g" \
    -e "s|__USER__|$(id -un)|g" \
    "$PLIST_TEMPLATE" > "$rendered"

  # A plist that does not parse is a job that silently never runs.
  if command -v plutil >/dev/null 2>&1; then
    if ! plutil -lint "$rendered" >/dev/null; then
      echo "ERROR: rendered plist failed plutil -lint; not installing." >&2
      rm -f "$rendered"
      exit 1
    fi
  fi

  install -m 644 "$rendered" "$PLIST_DST"
  rm -f "$rendered"

  # Replace any previous job, then load.
  launchctl bootout "${LAUNCHD_TARGET}/${LABEL}" 2>/dev/null || true
  launchctl bootstrap "${LAUNCHD_TARGET}" "$PLIST_DST"

  echo "installed ${LABEL}"
  echo "  plist:   ${PLIST_DST}"
  echo "  entry:   ${ENTRYPOINT}"
  echo "  env:     ${ENV_FILE} (vars: $(env_file_var_names "$ENV_FILE" | tr '\n' ' '))"
  echo "  logs:    ${LOG_DIR}/wake.out.log  ${LOG_DIR}/wake.err.log"
  echo
  echo "The producer (PhenoBot) must be pointed at this receiver with:"
  echo "  BRIDGE_WAKE_URL_<PERSONA>=http://127.0.0.1:3211/wake"
  echo "  BRIDGE_TOKEN_<PERSONA>=<same value as WAKE_RECEIVER_TOKEN>"
  echo "  (see docs/agent-comms/README.md)"
}

# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------

do_uninstall() {
  launchctl bootout "${LAUNCHD_TARGET}/${LABEL}" 2>/dev/null || true
  rm -f "$PLIST_DST"
  echo "removed ${LABEL} (config and logs kept)"
}

# ---------------------------------------------------------------------------
# status (read-only)
# ---------------------------------------------------------------------------

do_status() {
  echo "label:    ${LABEL}"
  echo "plist:    ${PLIST_DST} $([ -f "$PLIST_DST" ] && echo '(installed)' || echo '(not installed)')"
  echo "entry:    ${ENTRYPOINT} $([ -f "$ENTRYPOINT" ] && echo '(ok)' || echo '(MISSING)')"
  echo "env:      ${ENV_FILE} $([ -f "$ENV_FILE" ] && echo "(vars: $(env_file_var_names "$ENV_FILE" | tr '\n' ' '))" || echo '(MISSING)')"
  echo
  echo "launchd:"
  launchctl list "${LABEL}" 2>/dev/null || echo "  (not loaded)"
  echo
  echo "health:"
  local port
  port="$(grep -E '^[[:space:]]*(export[[:space:]]+)?WAKE_RECEIVER_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2 | tr -d '[:space:]')"
  port="${port:-3211}"
  if curl -fsS -m 2 "http://127.0.0.1:${port}/healthz" >/dev/null 2>&1; then
    echo "  http://127.0.0.1:${port}/healthz -> ok"
  else
    echo "  http://127.0.0.1:${port}/healthz -> NOT REACHABLE"
  fi
  echo
  echo "log tail:"
  tail -n 10 "${LOG_DIR}/wake.out.log" 2>/dev/null || echo "  (no out log)"
  tail -n 10 "${LOG_DIR}/wake.err.log" 2>/dev/null || echo "  (no err log)"
}

case "${1:-}" in
  install) do_install ;;
  uninstall) do_uninstall ;;
  status) do_status ;;
  restart)
    launchctl bootout "${LAUNCHD_TARGET}/${LABEL}" 2>/dev/null || true
    launchctl bootstrap "${LAUNCHD_TARGET}" "$PLIST_DST"
    echo "restarted ${LABEL}"
    ;;
  *) usage ;;
esac
