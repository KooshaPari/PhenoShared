#!/usr/bin/env bash
# --profile-dir is the isolated PROJECT directory; native file is .mcp.json.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/../profile_install.py" forge "$@"
