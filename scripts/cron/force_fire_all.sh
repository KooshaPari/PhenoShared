#!/bin/bash
# scripts/cron/force_fire_all.sh — idempotent one-shot kickstart for all 4
# pheno-harness LaunchAgents.  Re-runnable: agents that are not loaded are
# bootstrapped first; agents that are already running are kicked.
#
# Usage:
#   bash scripts/cron/force_fire_all.sh             # fire all 4
#   bash scripts/cron/force_fire_all.sh sota-snapshot   # fire one
#
# Agents:
#   com.phenotype.pheno-harness.sota-snapshot
#   com.phenotype.pheno-harness.health-repo
#   com.phenotype.pheno-harness.worktree-gc
#   com.phenotype.pheno-harness.lint-branches

set -euo pipefail

AGENTS=(
  "com.phenotype.pheno-harness.sota-snapshot"
  "com.phenotype.pheno-harness.health-repo"
  "com.phenotype.pheno-harness.worktree-gc"
  "com.phenotype.pheno-harness.lint-branches"
)

UID_VAL="$(id -u)"
DOMAIN="gui/${UID_VAL}"
PLIST_DIR="${HOME}/Library/LaunchAgents"

# DRY_RUN=1 prints what would happen without launching anything.
DRY_RUN="${DRY_RUN:-0}"

fire_one() {
  local label="$1"
  local plist="${PLIST_DIR}/${label}.plist"
  local target="${DOMAIN}/${label}"

  if [[ ! -e "${plist}" ]]; then
    echo "[skip] ${label}: plist not installed at ${plist}" >&2
    echo "[hint] run: bash scripts/cron/install_launchd.sh install" >&2
    return 0
  fi

  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '  [dry-run] launchctl bootstrap %s %s  (if not loaded)\n' "${DOMAIN}" "${plist}"
    printf '  [dry-run] launchctl kickstart -k %s\n' "${target}"
    return 0
  fi

  # Bootstrap first if not yet loaded; ignore "Already loaded" output.
  if ! output=$(launchctl bootstrap "${DOMAIN}" "${plist}" 2>&1); then
    if [[ "${output}" != *"Already loaded"* ]]; then
      echo "[warn] bootstrap ${label}: ${output}" >&2
    fi
  fi

  if launchctl kickstart -k "${target}" 2>&1; then
    echo "[ok]   ${label}"
  else
    echo "[fail] ${label}" >&2
    return 1
  fi
}

case "${1:-}" in
  "")
    for label in "${AGENTS[@]}"; do
      fire_one "${label}"
    done
    ;;
  sota-snapshot|health-repo|worktree-gc|lint-branches)
    fire_one "com.phenotype.pheno-harness.${1}"
    ;;
  *)
    echo "Usage: $0 [sota-snapshot|health-repo|worktree-gc|lint-branches]" >&2
    echo "       (no arg = fire all 4; DRY_RUN=1 to print without firing)" >&2
    exit 2
    ;;
esac
