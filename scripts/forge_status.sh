#!/usr/bin/env bash
# scripts/forge_status.sh — unified status for the 3 forge-* launchd agents.
#
# v0.13 WBS-PERT-100 Phase 3 task 42 (forge_status.sh unified status).
#
# Reports, per agent:
# - Loaded? (PID + last-exit code via `launchctl list`)
# - Schedule (StartCalendarInterval)
# - Next run time (via `launchctl print`)
# - Last log line (tail -1 of the per-agent .log)
#
# Exit codes:
#   0  all 3 agents loaded + schedulable
#   1  usage error
#   2  one or more agents not loaded
#   3  unable to determine state (e.g. launchctl unavailable)
#
# Usage:
#   bash scripts/forge_status.sh            # human-readable table
#   bash scripts/forge_status.sh --json     # JSON output for scripts
#   bash scripts/forge_status.sh --quiet    # exit code only

set -euo pipefail

AGENTS=(
  "com.phenoforge.forge-watchdog:forge-watchdog.sh"
  "com.phenoforge.forge-net-heal:forge-net-heal.sh"
  "com.phenoforge.forge-proc-reap:forge-proc-reap.sh"
)
LABEL_PREFIX="com.phenoforge"
LOG_ROOT="${HOME}/.pheno-harness/logs"

MODE="table"
for arg in "$@"; do
  case "$arg" in
    --json)  MODE="json" ;;
    --quiet) MODE="quiet" ;;
    -h|--help)
      sed -n '2,18p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    *)
      echo "unknown arg: $arg" >&2
      exit 1
      ;;
  esac
done

# Collect status for each agent.
declare -a ROW_PID=()
declare -a ROW_EXIT=()
declare -a ROW_NEXT=()
declare -a ROW_LOG=()
declare -a ROW_AGENT=()
declare -a ROW_SCRIPT=()
LOADED=0
TOTAL=0
UNLOADABLE=0

for entry in "${AGENTS[@]}"; do
  agent_label="${entry%%:*}"
  script_name="${entry##*:}"
  TOTAL=$((TOTAL + 1))
  ROW_AGENT+=("$agent_label")
  ROW_SCRIPT+=("$script_name")

  if ! command -v launchctl >/dev/null 2>&1; then
    ROW_PID+=("-")
    ROW_EXIT+=("?")
    ROW_NEXT+=("launchctl unavailable")
    ROW_LOG+=("(n/a)")
    UNLOADABLE=$((UNLOADABLE + 1))
    continue
  fi

  # launchctl list "<label>" →  "PID  Status  Label" for periodic agents,
  # or a YAML block for OnDemand agents. Only the periodic-style first
  # line is useful for our table; ignore everything else.
  list_out="$(launchctl list "$agent_label" 2>/dev/null || true)"
  first_line="$(printf '%s' "$list_out" | head -n 1)"
  if [[ -z "$first_line" ]]; then
    ROW_PID+=("-")
    ROW_EXIT+=("?")
    ROW_NEXT+=("(not loaded)")
    ROW_LOG+=("(no log)")
    continue
  fi
  # Periodic agents: PID and EXIT are the first two whitespace-separated
  # fields and the third is the label. OnDemand agents: line begins
  # with `{`. Treat the OnDemand case as loaded with no schedule info.
  if [[ "$first_line" =~ ^\{ ]]; then
    LOADED=$((LOADED + 1))
    ROW_PID+=("(on demand)")
    ROW_EXIT+=("(on demand)")
    ROW_NEXT+=("(on demand)")
  else
    LOADED=$((LOADED + 1))
    pid="$(awk '{print $1}' <<<"$first_line")"
    last_exit="$(awk '{print $2}' <<<"$first_line")"
    ROW_PID+=("$pid")
    ROW_EXIT+=("$last_exit")
    # Periodic agents have a "next run" line in `launchctl print` output.
    print_out="$(launchctl print "gui/$(id -u)/$agent_label" 2>/dev/null | awk '/next run/{print; exit}' || true)"
    if [[ -z "$print_out" ]]; then
      print_out="(unknown)"
    fi
    print_out="$(printf '%s' "$print_out" | sed 's/^ *//; s/ *$//' | cut -c1-32)"
    ROW_NEXT+=("$print_out")
  fi

  # Tail the per-agent log if present.
  log_path="${LOG_ROOT}/${agent_label}.log"
  if [[ -f "$log_path" ]]; then
    last="$(tail -1 "$log_path" 2>/dev/null || true)"
    ROW_LOG+=("${last:-(empty)}")
  else
    ROW_LOG+=("(no log)")
  fi
done

# Emit output.
emit_table() {
  printf '%-44s %-6s %-6s %-32s %s\n' "AGENT" "PID" "EXIT" "NEXT-RUN" "LAST-LOG"
  printf '%-44s %-6s %-6s %-32s %s\n' "$(printf -- '-%.0s' {1..44})" "------" "------" "$(printf -- '-%.0s' {1..32})" "--------"
  for i in "${!ROW_AGENT[@]}"; do
    printf '%-44s %-6s %-6s %-32s %s\n' \
      "${ROW_AGENT[$i]}" \
      "${ROW_PID[$i]}" \
      "${ROW_EXIT[$i]}" \
      "${ROW_NEXT[$i]}" \
      "${ROW_LOG[$i]}"
  done
}

emit_json() {
  printf '{\n'
  printf '  "agents": [\n'
  for i in "${!ROW_AGENT[@]}"; do
    sep="$([[ $i -lt $((${#ROW_AGENT[@]} - 1)) ]] && echo "," || echo "")"
    printf '    {"label": "%s", "script": "%s", "pid": "%s", "last_exit": "%s", "next_run": "%s", "last_log": "%s"}%s\n' \
      "${ROW_AGENT[$i]}" \
      "${ROW_SCRIPT[$i]}" \
      "${ROW_PID[$i]}" \
      "${ROW_EXIT[$i]}" \
      "${ROW_NEXT[$i]}" \
      "${ROW_LOG[$i]}" \
      "$sep"
  done
  printf '  ],\n'
  printf '  "loaded": %d,\n  "total": %d,\n  "unloadable": %d\n' \
    "$LOADED" "$TOTAL" "$UNLOADABLE"
  printf '}\n'
}

case "$MODE" in
  table) emit_table ;;
  json)  emit_json ;;
  quiet)
    if (( UNLOADABLE > 0 )); then exit 3; fi
    if (( LOADED < TOTAL )); then exit 2; fi
    exit 0
    ;;
esac

if (( UNLOADABLE > 0 )); then exit 3; fi
if (( LOADED < TOTAL )); then exit 2; fi
exit 0
