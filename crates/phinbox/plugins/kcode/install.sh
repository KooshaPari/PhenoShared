#!/usr/bin/env bash
# Explicit independent kcode profile; dry-run unless --apply.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/../profile_install.py" kcode "$@"
