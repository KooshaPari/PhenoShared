#!/usr/bin/env bash
# Explicit isolated profile only; dry-run unless --apply. Existing hooks are untouched.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/../profile_install.py" codex "$@"
