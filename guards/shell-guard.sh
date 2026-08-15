#!/usr/bin/env bash
# Minimal shell guard for Claude hook PreToolUse.
# Keeps hooks fast by doing a lightweight local policy check and never hard-fails.
set -euo pipefail

INPUT_JSON="$(cat 2>/dev/null || true)"
TOOL="Bash"
COMMAND=""

if [[ -n "$INPUT_JSON" ]]; then
  # Parse stdin payload if provided by Claude hook.
  if command -v python3 >/dev/null 2>&1; then
    COMMAND="$(printf '%s' "$INPUT_JSON" | python3 - "$PWD" <<'PY'
import json, sys
raw = sys.stdin.read() or "{}"
try:
    data = json.loads(raw)
except Exception:
    data = {}

tool = data.get("tool") or data.get("tool_name") or "Bash"
command = ""
tool_input = data.get("tool_input") or data.get("input") or {}
if isinstance(tool_input, dict):
    command = tool_input.get("command") or tool_input.get("code") or ""
if not command:
    command = data.get("command", "")

print(str(tool))
print(str(command))
PY
 )"
    # Preserve tool and command for optional policy check.
    TOOL="${COMMAND%%$'\n'*}"
    COMMAND="${COMMAND#*$'\n'}"
  fi
fi

# If a direct CLI arg was passed, keep compatibility.
if [[ $# -ge 1 ]]; then
  COMMAND="$*"
fi

if [[ -x "/Users/kooshapari/.claude/bin/policy-gate-check.sh" ]] && [[ -n "$COMMAND" ]]; then
  "/Users/kooshapari/.claude/bin/policy-gate-check.sh" "$TOOL" "$COMMAND" >/dev/null 2>&1 || {
    # Policy gate blocks with exit code 2; propagate while keeping noise low.
    exit $?
  }
fi

exit 0

