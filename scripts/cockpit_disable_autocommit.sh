#!/usr/bin/env bash
# scripts/cockpit_disable_autocommit.sh — set COCKPIT_DEPRECATED=1 system-wide.
#
# v0.13 WBS-PERT-100 Phase 5 task 74 — disable cockpit autocommit.
#
# Idempotent: re-running confirms the flag is set.
#
# Use:
#   bash scripts/cockpit_disable_autocommit.sh
#   bash scripts/cockpit_disable_autocommit.sh --revert

set -euo pipefail

ENV_FILE="${HOME}/.pheno-harness/env.sh"

action="install"
for arg in "$@"; do
  case "$arg" in
    --revert) action="uninstall" ;;
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

mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"

case "$action" in
  install)
  if grep -q '^export COCKPIT_DEPRECATED=1' "$ENV_FILE" 2>/dev/null; then
    echo "COCKPIT_DEPRECATED already set in $ENV_FILE" >&2
    exit 0
  fi
  {
    echo ""
    echo "# v0.13 Phase 5 task 74 — disable cockpit autocommit daemon."
    echo "export COCKPIT_DEPRECATED=1"
  } >> "$ENV_FILE"
  echo "added COCKPIT_DEPRECATED=1 to $ENV_FILE" >&2
  echo "to apply now:  source $ENV_FILE" >&2
  ;;

  uninstall)
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "no env file at $ENV_FILE; nothing to do" >&2
    exit 0
  fi
  # Idempotent: strip any COCKPIT_DEPRECATED line (commented or not).
  if grep -q 'COCKPIT_DEPRECATED' "$ENV_FILE"; then
    tmp="$(mktemp -t cockpitrevert.XXXXXX)"
    grep -v 'COCKPIT_DEPRECATED' "$ENV_FILE" > "$tmp"
    mv "$tmp" "$ENV_FILE"
    echo "removed COCKPIT_DEPRECATED from $ENV_FILE" >&2
  else
    echo "COCKPIT_DEPRECATED not set; nothing to do" >&2
  fi
  ;;
esac

exit 0
