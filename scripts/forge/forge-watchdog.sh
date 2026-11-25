#!/usr/bin/env bash
# forge-watchdog.sh — host-side system health watchdog (v0.12 phase 3).
#
# Monitors disk usage, memory pressure, and process count on the host.
# Installed at ~/.forge/bin/forge-watchdog.sh and invoked by the
# com.phenoforge.forge-watchdog launchd plist with the `check` subcommand.
#
# Subcommands:
#   status  — print human-readable stats for disk/mem/proc.
#   check   — emit a JSON line per threshold violation; exit 1 on any
#             breach (disk >=95%, mem used >=90%, procs > 1000).
#   report  — dump a markdown table summary.
#
# Thresholds (set by WBS-PERT-100 v0.12 tasks 37-39):
#   DISK_PCT_WARN = 95     (df -P percent of ${HOME} volume)
#   MEM_PCT_WARN  = 90     (vm_stat percent of total memory used)
#   PROC_WARN     = 1000   (ps -ax process count)
#
# Exit codes:
#   0 = healthy (check sub-command only)
#   1 = degraded (at least one threshold breached)
#   2 = invocation error

set -uo pipefail

readonly DISK_PCT_WARN=95
readonly MEM_PCT_WARN=90
readonly PROC_WARN=1000

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

usage() {
  cat <<USAGE
forge-watchdog.sh — host-side system health watchdog

Usage:
  forge-watchdog.sh status   # print disk/mem/proc stats (human-readable)
  forge-watchdog.sh check    # JSON-lines per breach; non-zero exit if breached
  forge-watchdog.sh report   # markdown summary table
USAGE
}

# --- disk usage ---------------------------------------------------------
# Returns: DISK_PCT (integer percent used on ${HOME})
gather_disk() {
  # df -P "$HOME" — second row, fifth column (Use%), strip the '%'
  local pct
  pct=$(df -P "${HOME}" 2>/dev/null | awk 'NR==2 {sub("%","",$5); print $5}')
  if [ -z "${pct:-}" ]; then
    pct=0
  fi
  printf '%s' "${pct}"
}

# --- memory usage -------------------------------------------------------
# Returns: MEM_USED_PCT (integer percent of total system memory used).
gather_mem() {
  # Total memory in bytes (sysctl hw.memsize)
  local total_bytes free_pages page_size free_bytes used_bytes pct
  total_bytes=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
  if [ "${total_bytes}" -eq 0 ]; then
    printf '0'
    return
  fi
  # vm_stat "Pages free: <N>." — extract integer
  free_pages=$(vm_stat 2>/dev/null | awk '/Pages free/ {gsub("\\.","",$3); print $3}')
  free_pages="${free_pages:-0}"
  # Page size from hw.pagesize (usually 16384 on Apple Silicon)
  page_size=$(sysctl -n hw.pagesize 2>/dev/null || echo 4096)
  free_bytes=$((free_pages * page_size))
  if [ "${free_bytes}" -gt "${total_bytes}" ]; then
    free_bytes="${total_bytes}"
  fi
  used_bytes=$((total_bytes - free_bytes))
  pct=$((used_bytes * 100 / total_bytes))
  printf '%s' "${pct}"
}

# --- process count ------------------------------------------------------
gather_procs() {
  ps -ax 2>/dev/null | wc -l | tr -d ' '
}

# --- status sub-command -------------------------------------------------
cmd_status() {
  local disk_pct mem_used_pct proc_count
  disk_pct=$(gather_disk)
  mem_used_pct=$(gather_mem)
  proc_count=$(gather_procs)

  echo "=== forge-watchdog status ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
  echo
  echo "disk used (${HOME}):       ${disk_pct}%  (warn at >=${DISK_PCT_WARN}%)"
  echo "memory used (system-wide): ${mem_used_pct}%  (warn at >=${MEM_PCT_WARN}%)"
  echo "process count:             ${proc_count}    (warn at >${PROC_WARN})"
  echo
  if [ "${disk_pct}" -ge "${DISK_PCT_WARN}" ]; then
    echo "STATUS: DISK PRESSURE"
  elif [ "${mem_used_pct}" -ge "${MEM_PCT_WARN}" ]; then
    echo "STATUS: MEMORY PRESSURE"
  elif [ "${proc_count}" -gt "${PROC_WARN}" ]; then
    echo "STATUS: PROCESS SATURATION"
  else
    echo "STATUS: healthy"
  fi
}

# --- check sub-command --------------------------------------------------
# Emits a single JSON object per line for each threshold violation.
# Exits 1 if any threshold is breached; exits 0 if all healthy.
cmd_check() {
  local disk_pct mem_used_pct proc_count exit_code=0 violation
  disk_pct=$(gather_disk)
  mem_used_pct=$(gather_mem)
  proc_count=$(gather_procs)

  # Always log to the launchd log file (stdout for launchd)
  log "watchdog check: disk=${disk_pct}% mem=${mem_used_pct}% procs=${proc_count}"

  if [ "${disk_pct}" -ge "${DISK_PCT_WARN}" ]; then
    violation=$(printf '{"level":"ERROR","metric":"disk_used_pct","value":%s,"threshold":%s,"msg":"disk at %s%% on %s (>=%s%%)"}' \
      "${disk_pct}" "${DISK_PCT_WARN}" "${disk_pct}" "${HOME}" "${DISK_PCT_WARN}")
    printf '%s\n' "${violation}"
    exit_code=1
  fi

  if [ "${mem_used_pct}" -ge "${MEM_PCT_WARN}" ]; then
    violation=$(printf '{"level":"ERROR","metric":"memory_used_pct","value":%s,"threshold":%s,"msg":"memory at %s%% used (>=%s%%)"}' \
      "${mem_used_pct}" "${MEM_PCT_WARN}" "${mem_used_pct}" "${MEM_PCT_WARN}")
    printf '%s\n' "${violation}"
    exit_code=1
  fi

  if [ "${proc_count}" -gt "${PROC_WARN}" ]; then
    violation=$(printf '{"level":"ERROR","metric":"process_count","value":%s,"threshold":%s,"msg":"process count %s exceeds %s"}' \
      "${proc_count}" "${PROC_WARN}" "${proc_count}" "${PROC_WARN}")
    printf '%s\n' "${violation}"
    exit_code=1
  fi

  if [ "${exit_code}" -eq 0 ]; then
    log "watchdog: healthy (disk=${disk_pct}%, mem=${mem_used_pct}%, procs=${proc_count})"
  else
    log "watchdog: degraded (disk=${disk_pct}%, mem=${mem_used_pct}%, procs=${proc_count})"
  fi

  return "${exit_code}"
}

# --- report sub-command -------------------------------------------------
cmd_report() {
  local disk_pct mem_used_pct proc_count status_cell
  disk_pct=$(gather_disk)
  mem_used_pct=$(gather_mem)
  proc_count=$(gather_procs)

  if [ "${disk_pct}" -ge "${DISK_PCT_WARN}" ] || \
     [ "${mem_used_pct}" -ge "${MEM_PCT_WARN}" ] || \
     [ "${proc_count}" -gt "${PROC_WARN}" ]; then
    status_cell="DEGRADED"
  else
    status_cell="HEALTHY"
  fi

  cat <<MD
# forge-watchdog report — $(date -u +%Y-%m-%dT%H:%M:%SZ)

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| disk_used_pct (${HOME}) | ${disk_pct}% | >= ${DISK_PCT_WARN}% | $([ "${disk_pct}" -ge "${DISK_PCT_WARN}" ] && echo "BREACH" || echo "OK") |
| memory_used_pct | ${mem_used_pct}% | >= ${MEM_PCT_WARN}% | $([ "${mem_used_pct}" -ge "${MEM_PCT_WARN}" ] && echo "BREACH" || echo "OK") |
| process_count | ${proc_count} | > ${PROC_WARN} | $([ "${proc_count}" -gt "${PROC_WARN}" ] && echo "BREACH" || echo "OK") |

**Overall:** ${status_cell}
MD
}

# --- dispatch -----------------------------------------------------------
case "${1:-status}" in
  status) cmd_status ;;
  check)  cmd_check ;;
  report) cmd_report ;;
  -h|--help|help) usage ;;
  *)
    usage >&2
    exit 2
    ;;
esac
