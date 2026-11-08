# absorption-justification.sh
# ----------------------------------------------------------------------------
# Bash companion to bin/absorption-justification.py. Translates the most
# common invocation pattern into a single shell command so CI workflows that
# prefer bash over Python can still drive the orchestrator.
#
# Usage:
#   bash bin/absorption-justification.sh \
#     --repos <REDACTED>/foo,<REDACTED>/bar \
#     [--registry-root PATH] [--audits-dir PATH] \
#     [--template PATH] [--disposition PATH] \
#     [--dry-run] [--verbose]
#
# Exits 0 on full success, 1 on partial success, 2 on full failure.
# ----------------------------------------------------------------------------
set -uo pipefail

REPOS=""
REGISTRY_ROOT="."
AUDITS_DIR=""
TEMPLATE=""
DISPOSITION=""
DRY_RUN=0
VERBOSE=0

usage() {
  grep '^#' "$0" | sed -e 's/^# \?//'
  exit 64
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repos) REPOS="$2"; shift 2 ;;
    --registry-root) REGISTRY_ROOT="$2"; shift 2 ;;
    --audits-dir) AUDITS_DIR="$2"; shift 2 ;;
    --template) TEMPLATE="$2"; shift 2 ;;
    --disposition) DISPOSITION="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --verbose) VERBOSE=1; shift ;;
    -h|--help) usage ;;
    *) echo "[absorption-justification.sh] unknown argument: $1" >&2; exit 64 ;;
  esac
done

if [[ -z "$REPOS" ]]; then
  echo "[absorption-justification.sh] --repos is required" >&2
  exit 64
fi

# Resolve default paths when not provided
if [[ -z "$AUDITS_DIR" ]]; then
  AUDITS_DIR="${REGISTRY_ROOT}/audits/absorption-justifications"
fi
if [[ -z "$TEMPLATE" ]]; then
  # Search order:
  #   1. Orchestrator's own bin/ (canonical location on this machine)
  #   2. Sibling phenotype-tooling checkout next to the registry root
  #   3. Direct bin/ under the registry root
  #   4. Explicit env override $ABSORPTION_TEMPLATE
  for cand in \
      "$(dirname "$0")/ABSORPTION_TEMPLATE.md" \
      "${ABSORPTION_TEMPLATE:-}" \
      "${REGISTRY_ROOT}/../phenotype-tooling/bin/ABSORPTION_TEMPLATE.md" \
      "${REGISTRY_ROOT}/bin/ABSORPTION_TEMPLATE.md"; do
    if [[ -n "$cand" && -f "$cand" ]]; then
      TEMPLATE="$cand"; break
    fi
  done
fi
if [[ -z "$DISPOSITION" ]]; then
  DISPOSITION="${REGISTRY_ROOT}/registry/disposition-index.json"
fi

if [[ -z "$TEMPLATE" || ! -f "$TEMPLATE" ]]; then
  echo "[absorption-justification.sh] could not locate ABSORPTION_TEMPLATE.md" >&2
  exit 2
fi

PY="${PYTHON:-python}"
ARGS=(--repos "$REPOS" --registry-root "$REGISTRY_ROOT" --template "$TEMPLATE" --disposition "$DISPOSITION")
if [[ -n "$AUDITS_DIR" ]]; then ARGS+=(--audits-dir "$AUDITS_DIR"); fi
if [[ $DRY_RUN -eq 1 ]]; then ARGS+=(--dry-run); fi
if [[ $VERBOSE -eq 1 ]]; then ARGS+=(--verbose); fi

exec "$PY" "$(dirname "$0")/absorption-justification.py" "${ARGS[@]}"