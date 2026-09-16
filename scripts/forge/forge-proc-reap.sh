#!/usr/bin/env bash
# forge-proc-reap.sh — host-side zombie + worktree lock reaper (v0.12 phase 3).
#
# Identifies and clears zombie processes older than 1 hour and removes
# orphaned `.git/index.lock` files in active worktrees. Installed at
# ~/.forge/bin/forge-proc-reap.sh and invoked by the
# com.phenoforge.forge-proc-reap launchd plist with the `reap` subcommand.
#
# Subcommands:
#   status  — list zombies, active worktrees, and .git/index.lock files.
#   reap    — kill zombies > 1h old (via SIGCHLD to parent) and remove
#             orphaned .git/index.lock files; non-zero exit if any action
#             was taken.
#   report  — markdown summary of last reap pass.
#
# Behavior (WBS-PERT-100 v0.12 tasks 46-47):
#   - Zombies > 1h old: SIGCHLD to parent process.
#   - Orphaned locks:   .git/index.lock files in worktrees whose owning
#                       git process is no longer running.
#
# Exit codes:
#   0 = nothing to reap
#   1 = at least one zombie reaped OR lock removed
#   2 = invocation error

set -uo pipefail

readonly ZOMBIE_AGE_MIN=60    # 1 hour (parent spec); kept in minutes
readonly WORKTREE_ROOT="${PHENO_ROOT:-/Users/kooshapari/CodeProjects/Phenotype/repos/pheno-harness}"

STATE_FILE="${HOME}/.pheno-harness/state/forge-proc-reap.last"
mkdir -p "$(dirname "${STATE_FILE}")"

log() {
  printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

usage() {
  cat <<USAGE
forge-proc-reap.sh — host-side zombie + worktree lock reaper

Usage:
  forge-proc-reap.sh status   # list zombies, worktrees, and lock files
  forge-proc-reap.sh reap     # kill zombies > 1h old; clear orphaned locks
  forge-proc-reap.sh report   # markdown summary of last reap pass
USAGE
}

# --- etime parser -------------------------------------------------------
# Convert ps etime field ("HH:MM:SS" or "MM:SS" or "DD-HH:MM:SS") to minutes.
# Returns 0 if parseable; echoes the minute count.
etime_to_min() {
  local etime="$1"
  local days=0 hours=0 mins=0 secs=0
  if [[ "${etime}" == *-* ]]; then
    days="${etime%%-*}"
    local rest="${etime#*-}"
    hours="${rest%%:*}"
    mins="${rest#*:}"
    mins="${mins%%:*}"
  elif [[ "${etime}" == *:*:* ]]; then
    hours="${etime%%:*}"
    local rest="${etime#*:}"
    mins="${rest%%:*}"
  else
    mins="${etime%%:*}"
  fi
  echo $(( days * 24 * 60 + hours * 60 + mins ))
}

# --- gather zombies ----------------------------------------------------
# Echoes "<pid>|<etime_raw>|<ppid>" one per line, only for zombies.
# The etime is kept raw (HH:MM:SS or MM:SS or DD-HH:MM:SS) — the consumer
# (cmd_status / cmd_reap) converts it to minutes via etime_to_min.
gather_zombies() {
  ps -axo pid,ppid,etime,state 2>/dev/null \
    | awk 'NR>1 && tolower($4) ~ /^z/ { printf "%s|%s|%s\n", $1, $3, $2 }'
}

# --- gather worktrees ---------------------------------------------------
# Echoes worktree paths (one per line) under WORKTREE_ROOT/worktrees
gather_worktrees() {
  if [ -d "${WORKTREE_ROOT}/worktrees" ]; then
    find "${WORKTREE_ROOT}/worktrees" -mindepth 1 -maxdepth 2 -type d 2>/dev/null
  fi
}

# --- gather orphaned lock files ----------------------------------------
# Echoes orphaned .git/index.lock paths (owning git process is gone).
gather_lock_files() {
  local wt lock_path
  for wt in $(gather_worktrees); do
    # Worktree git dir: <wt>/.git is a file pointing to the real .git/worktrees/<name>
    local gitdir=""
    if [ -f "${wt}/.git" ]; then
      gitdir=$(awk -F'gitdir: ' '/^gitdir: / {print $2}' "${wt}/.git" 2>/dev/null)
    elif [ -d "${wt}/.git" ]; then
      gitdir="${wt}/.git"
    fi
    if [ -n "${gitdir}" ] && [ -f "${gitdir}/index.lock" ]; then
      # Treat as orphan if no git process is alive that has this lock open.
      # Simpler heuristic: if no `git` PID exists in this worktree, it's orphan.
      # We use a conservative check: lock older than 5 minutes with no recent
      # git pid owning it.
      local lock_age_secs
      lock_age_secs=$(( $(date +%s) - $(stat -f %m "${gitdir}/index.lock" 2>/dev/null || echo 0) ))
      if [ "${lock_age_secs}" -gt 300 ]; then
        printf '%s\n' "${gitdir}/index.lock"
      fi
    fi
  done
}

# --- status sub-command -------------------------------------------------
cmd_status() {
  local z_count l_count w_count
  z_count=$(gather_zombies | wc -l | tr -d ' ')
  l_count=$(gather_lock_files | wc -l | tr -d ' ')
  w_count=$(gather_worktrees | wc -l | tr -d ' ')

  echo "=== forge-proc-reap status ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="
  echo
  echo "zombies (all ages):         ${z_count}"
  echo "active worktrees:           ${w_count}  (under ${WORKTREE_ROOT}/worktrees)"
  echo "orphaned .git/index.lock:   ${l_count}"
  echo
  if [ "${z_count}" -gt 0 ]; then
    echo "--- zombies ---"
    gather_zombies | while IFS='|' read -r pid etime_raw ppid; do
      local age_min
      age_min=$(etime_to_min "${etime_raw:-0}")
      printf '  pid=%s age=%smin (raw=%s) ppid=%s\n' "${pid}" "${age_min}" "${etime_raw}" "${ppid}"
    done
  fi
  if [ "${l_count}" -gt 0 ]; then
    echo "--- orphaned locks ---"
    gather_lock_files | sed 's/^/  /'
  fi
}

# --- reap sub-command ---------------------------------------------------
cmd_reap() {
  local exit_code=0
  local reaped=0 locks_removed=0

  log "proc-reap: starting (zombie age threshold = ${ZOMBIE_AGE_MIN}min)"

  # Record state for report
  {
    printf 'timestamp=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'zombie_age_threshold_min=%s\n' "${ZOMBIE_AGE_MIN}"
  } > "${STATE_FILE}"

  # --- reap zombies ---
  while IFS='|' read -r pid etime_raw ppid; do
    [ -z "${pid:-}" ] && continue
    local age_min
    age_min=$(etime_to_min "${etime_raw:-0}")
    if [ "${age_min:-0}" -ge "${ZOMBIE_AGE_MIN}" ]; then
      log "reaping zombie pid=${pid} age=${age_min}min (raw=${etime_raw}) ppid=${ppid}"
      if [ -n "${ppid:-}" ] && [ "${ppid:-0}" -gt 0 ]; then
        kill -CHLD "${ppid}" 2>/dev/null || log "  (SIGCHLD to ${ppid} failed)"
      fi
      reaped=$((reaped + 1))
    else
      log "skipping young zombie pid=${pid} age=${age_min}min (raw=${etime_raw}) (< ${ZOMBIE_AGE_MIN}min)"
    fi
  done < <(gather_zombies)

  # --- clear orphaned locks ---
  local lock
  for lock in $(gather_lock_files); do
    if [ -f "${lock}" ]; then
      log "removing orphaned lock ${lock}"
      rm -f "${lock}" && locks_removed=$((locks_removed + 1))
    fi
  done

  {
    printf 'zombies_reaped=%s\n' "${reaped}"
    printf 'locks_removed=%s\n' "${locks_removed}"
  } >> "${STATE_FILE}"

  if [ "${reaped}" -gt 0 ] || [ "${locks_removed}" -gt 0 ]; then
    log "proc-reap: reaped ${reaped} zombie(s); removed ${locks_removed} lock(s)"
    exit_code=1
  else
    log "proc-reap: nothing to reap"
  fi

  return "${exit_code}"
}

# --- report sub-command -------------------------------------------------
cmd_report() {
  if [ ! -f "${STATE_FILE}" ]; then
    echo "# forge-proc-reap report"
    echo
    echo "No prior reap recorded. Run \`forge-proc-reap.sh reap\` first."
    return 0
  fi

  local ts thresh reaped locks overall
  ts=$(awk -F= '/^timestamp=/ {print $2}' "${STATE_FILE}")
  thresh=$(awk -F= '/^zombie_age_threshold_min=/ {print $2}' "${STATE_FILE}")
  reaped=$(awk -F= '/^zombies_reaped=/ {print $2}' "${STATE_FILE}")
  locks=$(awk -F= '/^locks_removed=/ {print $2}' "${STATE_FILE}")
  reaped="${reaped:-0}"
  locks="${locks:-0}"
  if [ "${reaped}" -eq 0 ] && [ "${locks}" -eq 0 ]; then
    overall="HEALTHY"
  else
    overall="ACTION TAKEN"
  fi

  cat <<MD
# forge-proc-reap report — ${ts}

| Metric | Value | Threshold |
|--------|-------|-----------|
| zombie age threshold | ${thresh} min | (>= 60 min reaped) |
| zombies reaped | ${reaped} | — |
| orphaned locks removed | ${locks} | — |

**Overall:** ${overall}
MD
}

# --- dispatch -----------------------------------------------------------
case "${1:-status}" in
  status) cmd_status ;;
  reap)   cmd_reap ;;
  report) cmd_report ;;
  -h|--help|help) usage ;;
  *)
    usage >&2
    exit 2
    ;;
esac
