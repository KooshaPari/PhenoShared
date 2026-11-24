#!/usr/bin/env bash
# AgilePlus — Unix launcher
set -euo pipefail
AP_HOME="${AP_HOME:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$AP_HOME"
echo "=== AgilePlus launcher (Unix) ==="

if command -v process-compose >/dev/null 2>&1; then
    exec process-compose up -f process-compose.yml
fi

# Subsystem fallback
[[ -d "$AP_HOME/apps/byteport" ]] && (cd "$AP_HOME/apps/byteport" && npm run dev) &
[[ -d "$AP_HOME/desktop/electrobun" ]] && (cd "$AP_HOME/desktop/electrobun" && bun run dev) &

wait
