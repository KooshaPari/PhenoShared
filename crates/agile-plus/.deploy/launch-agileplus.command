#!/usr/bin/env bash
# AgilePlus — macOS launcher
set -euo pipefail
cd "$(dirname "$0")/.."
BASE="$(pwd)"
echo "=== AgilePlus launcher (macOS) ==="

if command -v process-compose >/dev/null 2>&1; then
    process-compose up -f process-compose.yml
    open "http://localhost:3000"
    exit $?
fi

[[ -d "$BASE/apps/byteport" ]] && (cd "$BASE/apps/byteport" && npm run dev) &
[[ -d "$BASE/desktop/electrobun" ]] && (cd "$BASE/desktop/electrobun" && bun run dev) &

sleep 3
open "http://localhost:3000"
wait
