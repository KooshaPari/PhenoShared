#!/bin/bash
# refresh-agileplus-token.sh — rotate the AgilePlus API bearer token.
#
# v0.12 WBS-PERT-100 task 32 (Phase 2 — AgilePlus token rotation) ac_v1.
#
# Usage:
#   ./refresh-agileplus-token.sh [--config <path>] [--dry-run] [--print-only]
#
# Behavior:
#   1. Reads ~/.agileplus/config.json (or --config <path>) for host/port/
#      api_token_env + current api_token_env value.
#   2. POSTs to <host>:<port>/auth/token/refresh with the current bearer
#      token in the Authorization header.
#   3. Server returns {"token": "<new-token>", "expires_at": "<iso8601>"}.
#   4. Writes the new token to ~/.agileplus/config.json under the
#      api_token field (preserving all other fields).
#
# Flags:
#   --config <path>   Use a non-default config file.
#   --dry-run         Print the new token but do NOT persist it.
#   --print-only      Don't even call the server — just print the env
#                     var's current value (for scripts that need it).
#
# Exit codes:
#   0  token refreshed and persisted (or printed in --dry-run/--print-only)
#   1  refresh failed (transport / auth / parse)
#   2  invalid arguments

set -e

PHENO_HARNESS_ROOT="${PHENO_HARNESS_ROOT:-/Users/<REDACTED>/CodeProjects/Phenotype/repos/pheno-harness}"

CONFIG_PATH="${AGILEPLUS_CONFIG:-$HOME/.agileplus/config.json}"
DRY_RUN=0
PRINT_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --config) CONFIG_PATH="$2"; shift ;;
    --dry-run) DRY_RUN=1 ;;
    --print-only) PRINT_ONLY=1 ;;
    -h|--help)
      sed -n '3,30p' "$0"
      exit 0
      ;;
    *) echo "ERROR: unknown flag: $1" >&2; exit 2 ;;
  esac
  shift
done

# Print-only: just emit the env var's current value.
if [ "$PRINT_ONLY" = "1" ]; then
  PHENO_HARNESS_ROOT="$PHENO_HARNESS_ROOT" python3 -c "
import json, os, sys
sys.path.insert(0, '$PHENO_HARNESS_ROOT')
from beads.agileplus_adapter.config import load_config, resolve_token
cfg = load_config('$CONFIG_PATH')
token = resolve_token(cfg) or ''
print(token)
"
  exit 0
fi

# Read current config + token.
PHENO_HARNESS_ROOT="$PHENO_HARNESS_ROOT" python3 -c "
import json, os, sys
sys.path.insert(0, '$PHENO_HARNESS_ROOT')
from beads.agileplus_adapter.config import load_config, resolve_token

cfg = load_config('$CONFIG_PATH')
current = resolve_token(cfg) or ''
host = cfg.get('host', '127.0.0.1')
port = cfg.get('port', 8080)
print(json.dumps({'host': host, 'port': port, 'current_token': current}))
" > /tmp/refresh-token.$$.json || {
  echo "ERROR: failed to read config at $CONFIG_PATH" >&2
  exit 1
}

CURRENT_HOST=$(python3 -c "import json; d=json.load(open('/tmp/refresh-token.$$.json')); print(d['host'])")
CURRENT_PORT=$(python3 -c "import json; d=json.load(open('/tmp/refresh-token.$$.json')); print(d['port'])")
CURRENT_TOKEN=$(python3 -c "import json; d=json.load(open('/tmp/refresh-token.$$.json')); print(d['current_token'])")
rm -f /tmp/refresh-token.$$.json

if [ -z "$CURRENT_TOKEN" ]; then
  echo "ERROR: no current token found (env var \$AGILEPLUS_API_TOKEN is unset)" >&2
  exit 1
fi

# POST to /auth/token/refresh.
REFRESH_RESPONSE=$(PHENO_HARNESS_ROOT="$PHENO_HARNESS_ROOT" python3 -c "
import json
import urllib.error
import urllib.request
url = f'http://{$CURRENT_HOST}:{$CURRENT_PORT}/auth/token/refresh'
req = urllib.request.Request(
    url, method='POST',
    headers={
        'Authorization': 'Bearer $CURRENT_TOKEN',
        'Content-Type': 'application/json',
    },
    data=b'{}',
)
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        print(response.read().decode())
except urllib.error.HTTPError as exc:
    print(f'HTTP {exc.code}: {exc.read(512).decode(errors=\"replace\")}', file=__import__('sys').stderr)
    raise SystemExit(1)
except urllib.error.URLError as exc:
    print(f'transport error: {exc}', file=__import__('sys').stderr)
    raise SystemExit(1)
") || {
  echo "ERROR: refresh request failed (server=$CURRENT_HOST:$CURRENT_PORT)" >&2
  exit 1
}

NEW_TOKEN=$(echo "$REFRESH_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin).get('token', ''))")
EXPIRES_AT=$(echo "$REFRESH_RESPONSE" | python3 -c "import json, sys; print(json.load(sys.stdin).get('expires_at', ''))")

if [ -z "$NEW_TOKEN" ]; then
  echo "ERROR: refresh response missing 'token' field: $REFRESH_RESPONSE" >&2
  exit 1
fi

echo "Refreshed token (expires_at=$EXPIRES_AT): ${NEW_TOKEN:0:8}..."

if [ "$DRY_RUN" = "1" ]; then
  echo "(dry-run: not persisted)"
  echo "$NEW_TOKEN"
  exit 0
fi

# Persist new token back to config.json (preserve all other fields).
PHENO_HARNESS_ROOT="$PHENO_HARNESS_ROOT" python3 -c "
import json
import sys
sys.path.insert(0, '$PHENO_HARNESS_ROOT')
from beads.agileplus_adapter.config import load_config
cfg = load_config('$CONFIG_PATH')
cfg['api_token'] = '$NEW_TOKEN'
if '$EXPIRES_AT':
    cfg['api_token_expires_at'] = '$EXPIRES_AT'
with open('$CONFIG_PATH', 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, sort_keys=True)
    f.write('\n')
print(f'  wrote new token to $CONFIG_PATH')
"

echo "Token rotation complete."
