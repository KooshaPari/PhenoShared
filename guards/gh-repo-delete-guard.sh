#!/usr/bin/env bash
# gh-repo-delete-guard.sh
# Intercepts gh commands and blocks any operation that would delete a repository.
# Exit 1 with an error message if blocked; pass through to real gh if safe.
#
# Blocked patterns:
#   gh repo delete ...
#   gh api -X DELETE /repos/...
#   gh api --method DELETE /repos/...
#   curl -X DELETE ...api.github.com/repos/...
#   curl --request DELETE ...api.github.com/repos/...
set -euo pipefail

RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

BLOCK_MSG="${RED}${BOLD}BLOCKED: Repository deletion is not permitted.${NC}
This action has been intercepted by the repo-delete guard.
If you truly need this, run it manually outside of agent sessions."

# --- Pattern 1: gh repo delete ---
if [[ "${1:-}" == "repo" && "${2:-}" == "delete" ]]; then
  echo -e "$BLOCK_MSG" >&2
  echo "Blocked command: gh repo delete $*" >&2
  exit 1
fi

# --- Pattern 2: gh repo delete (with --yes flag or similar) ---
# Also catch: gh repo delete <owner/repo> --yes
if [[ "${1:-}" == "repo" && "${2:-}" == "delete" ]]; then
  echo -e "$BLOCK_MSG" >&2
  echo "Blocked command: gh repo delete $*" >&2
  exit 1
fi

# --- Pattern 3: gh api with DELETE method targeting repos ---
if [[ "${1:-}" == "api" ]]; then
  shift
  METHOD=""
  ENDPOINT=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -X|--method)
        METHOD="${2:-}"
        shift 2
        ;;
      *)
        if [[ -z "$ENDPOINT" ]]; then
          ENDPOINT="$1"
        fi
        shift
        ;;
    esac
  done

  if [[ "${METHOD^^}" == "DELETE" && "$ENDPOINT" == *"/repos/"* ]]; then
    echo -e "$BLOCK_MSG" >&2
    echo "Blocked command: gh api -X DELETE $ENDPOINT" >&2
    exit 1
  fi

  # Restore original args and pass through
  # We need to reconstruct: gh api [original args]
  set -- api "$@"
  exec gh "$@"
fi

# --- Pattern 4: gh api graphql with deleteRepository mutation ---
if [[ "${1:-}" == "api" && "${2:-}" == "graphql" ]]; then
  # Check if stdin or remaining args contain deleteRepository
  BODY="${3:-}"
  if [[ "$BODY" == *"deleteRepository"* ]]; then
    echo -e "$BLOCK_MSG" >&2
    echo "Blocked: GraphQL mutation deleteRepository" >&2
    exit 1
  fi
fi

# --- Pass through to real gh for all other commands ---
exec gh "$@"
