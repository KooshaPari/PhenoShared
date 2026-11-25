#!/bin/bash
# scripts/cron/install_launchd.sh — install / uninstall the four pheno-harness
# LaunchAgents on macOS.  Idempotent: safe to re-run.
#
# Usage:
#   bash scripts/cron/install_launchd.sh install [sota-hour]   # default sota-hour = 4
#   bash scripts/cron/install_launchd.sh uninstall
#
# Dry-run:
#   DRY_RUN=1 bash scripts/cron/install_launchd.sh install
#   DRY_RUN=1 bash scripts/cron/install_launchd.sh uninstall
#   Prints what would happen (plist paths, bootstrap/bootout calls, mkdirs,
#   chmods, rms) without actually modifying anything or talking to launchd.
#
# Installs:
#   - com.phenotype.pheno-harness.sota-snapshot        (daily, at <hour>:00)
#   - com.phenotype.pheno-harness.health-repo          (weekly, Mon 03:00)
#   - com.phenotype.pheno-harness.worktree-gc           (weekly, Wed 04:00)
#   - com.phenotype.pheno-harness.lint-branches        (weekly, Fri 04:00)
#
# Each agent's plist is written to ${HOME}/Library/LaunchAgents/ and then
# bootstrapped via `launchctl bootstrap gui/$(id -u)`.  Logs land in
# ~/.pheno-harness/logs/<label>.{log,err}.

set -euo pipefail
# IMPORTANT: disable globbing.  The plist template contains literal '*'
# (the daily-schedule sentinel); without -f, bash expands it to cwd filenames.
set -f

# DRY_RUN=1 prints what would happen without modifying anything or talking to
# launchd.  All side-effecting calls below are gated on this.
DRY_RUN="${DRY_RUN:-0}"

# Echo a command and (unless DRY_RUN=1) execute it.  Bash builtin `echo` is
# prefixed so the dry-run log is grep-friendly: every line starts with
# "  [dry-run]" or "  [run]".
run() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '  [dry-run] %s\n' "$*"
  else
    printf '  [run] %s\n' "$*" >&2
    "$@"
  fi
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3)"
LOGS_ROOT="${HOME}/.pheno-harness/logs"
PLIST_DIR="${HOME}/Library/LaunchAgents"

# SOTA snapshot agent uses an explicit hour (default 4)
SOTA_HOUR="${2:-4}"

# Schedules (LaunchAgent weekday convention: 0=Sun 1=Mon 2=Tue 3=Wed 4=Thu 5=Fri 6=Sat)
# Format: <script> <weekday> <hour> <minute>   weekday="*" means every day
SCHEDULE_sota="${SCRIPT_DIR}/snapshot_sota.py    *   ${SOTA_HOUR} 0"   # daily
SCHEDULE_health="${SCRIPT_DIR}/health_repo_cron.sh  2  3 0"          # Mon 03:00
SCHEDULE_worktree="${SCRIPT_DIR}/worktree_gc_cron.sh  3  4 0"        # Wed 04:00
SCHEDULE_lint="${SCRIPT_DIR}/lint_branches_cron.sh  5  4 0"          # Fri 04:00

render_plist() {
  local label="$1"
  local script_path="$2"
  local weekday="$3"
  local hour="$4"
  local minute="$5"
  local plist="${PLIST_DIR}/${label}.plist"
  local prog="$PY"
  if [[ "$script_path" == *.sh ]]; then
    prog="/bin/bash"
  fi
  # Compute the calendar block.  weekday="*" means every day (Hour+Minute only).
  local calendar_block
  if [ "$weekday" = "*" ]; then
    calendar_block="      <key>Hour</key><integer>${hour}</integer>
      <key>Minute</key><integer>${minute}</integer>"
  else
    calendar_block="      <key>Weekday</key><integer>${weekday}</integer>
      <key>Hour</key><integer>${hour}</integer>
      <key>Minute</key><integer>${minute}</integer>"
  fi
  # IMPORTANT: use unquoted heredoc (EOF, not 'EOF') so variables expand.
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '  [dry-run] cat > %s <<EOF ... EOF\n' "${plist}"
  else
    cat > "${plist}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>${label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${prog}</string>
    <string>${script_path}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
${calendar_block}
  </dict>
  <key>WorkingDirectory</key><string>${SCRIPT_DIR}/../..</string>
  <key>StandardOutPath</key><string>${LOGS_ROOT}/${label}.log</string>
  <key>StandardErrorPath</key><string>${LOGS_ROOT}/${label}.err</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
EOF
  fi
  echo "  ${plist}"
}

install() {
  run mkdir -p "${PLIST_DIR}" "${LOGS_ROOT}"
  echo "Installing 4 LaunchAgents:"
  render_plist "com.phenotype.pheno-harness.sota-snapshot"  ${SCHEDULE_sota}
  render_plist "com.phenotype.pheno-harness.health-repo"    ${SCHEDULE_health}
  render_plist "com.phenotype.pheno-harness.worktree-gc"     ${SCHEDULE_worktree}
  render_plist "com.phenotype.pheno-harness.lint-branches"  ${SCHEDULE_lint}

  # Bootstrap (modern macOS API; `launchctl load` is deprecated).
  # `gui/$(id -u)` is the per-user GUI domain.  bootstrap is idempotent:
  # re-running on an already-loaded agent errors "already loaded" — safe.
  local uid
  uid="$(id -u)"
  local bootstrap_failed=0
  for label in \
    "com.phenotype.pheno-harness.sota-snapshot" \
    "com.phenotype.pheno-harness.health-repo" \
    "com.phenotype.pheno-harness.worktree-gc" \
    "com.phenotype.pheno-harness.lint-branches"; do
    plist="${PLIST_DIR}/${label}.plist"
    run chmod 644 "${plist}"
    if [[ "${DRY_RUN}" == "1" ]]; then
      printf '  [dry-run] launchctl bootstrap gui/%s %s\n' "${uid}" "${plist}"
    elif ! output=$(launchctl bootstrap "gui/${uid}" "${plist}" 2>&1); then
      # "Already loaded" is fine — idempotent.
      if [[ "${output}" != *"Already loaded"* ]]; then
        echo "  [warn] bootstrap ${label}: ${output}" >&2
        bootstrap_failed=1
      fi
    fi
  done
  if [[ "${bootstrap_failed}" -eq 0 ]]; then
    echo "done.  Active agents:"
    launchctl list 2>/dev/null | grep com.phenotype.pheno-harness | head -5
  else
    echo "done; some bootstraps failed.  Inspect with: launchctl list | grep com.phenotype"
    return 1
  fi
}

uninstall() {
  echo "Uninstalling 4 LaunchAgents:"
  local uid
  uid="$(id -u)"
  for label in \
    "com.phenotype.pheno-harness.sota-snapshot" \
    "com.phenotype.pheno-harness.health-repo" \
    "com.phenotype.pheno-harness.worktree-gc" \
    "com.phenotype.pheno-harness.lint-branches"; do
    plist="${PLIST_DIR}/${label}.plist"
    if [[ -e "${plist}" ]]; then
      run launchctl bootout "gui/${uid}/${label}" 2>/dev/null || true
      run rm -f "${plist}"
      echo "  removed ${label}"
    fi
  done
}

case "${1:-}" in
  install)   install ;;
  uninstall) uninstall ;;
  *)
    echo "Usage: $0 install [sota-hour] | uninstall   (DRY_RUN=1 for dry-run)" >&2
    exit 2
    ;;
esac
