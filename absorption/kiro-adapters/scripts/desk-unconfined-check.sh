#!/usr/bin/env bash
# desk-unconfined-check.sh
#
# Read-only probe: inspect a log file for evidence that a "desk" agent execution
# ran WITHOUT a native OS sandbox wrapper.
#
# Usage: scripts/desk-unconfined-check.sh <log-path>
#
# Output (exactly one line):
#   UNCONFINED <matched line>   -> the log shows sandbox_allow_unsandboxed_exec
#                                 or the phrase "no native OS wrapper"
#   CONFINED                    -> the log was readable and showed neither
#   UNKNOWN no-evidence         -> the log could not be read / did not exist
#
# Exit codes:
#   0  UNCONFINED
#   1  CONFINED
#   2  UNKNOWN
#
# This script never writes to any config, state, or log file.

set -uo pipefail

readonly PATTERN='sandbox_allow_unsandboxed_exec|no native OS wrapper'

usage() {
  printf 'usage: %s <log-path>\n' "$(basename "$0")" >&2
}

if [ "$#" -ne 1 ]; then
  usage
  printf 'UNKNOWN no-evidence\n'
  exit 2
fi

log_path="$1"

if [ -z "$log_path" ] || [ ! -f "$log_path" ] || [ ! -r "$log_path" ]; then
  printf 'UNKNOWN no-evidence\n'
  exit 2
fi

matched_line="$(grep -E -m 1 -i -- "$PATTERN" "$log_path" 2>/dev/null || true)"

if [ -n "$matched_line" ]; then
  printf 'UNCONFINED %s\n' "$matched_line"
  exit 0
fi

printf 'CONFINED\n'
exit 1
