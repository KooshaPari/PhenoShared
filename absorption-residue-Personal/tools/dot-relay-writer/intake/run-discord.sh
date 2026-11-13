#!/bin/bash
# Poller with the Discord leg. Token is fetched from Infisical into this process only.
set -euo pipefail
export HOME=/root
CREDS=/root/.infisical/bridges-creds.json
TOK=$(infisical login --method=universal-auth --client-id="$(python3 -c "import json;print(json.load(open('$CREDS'))['clientId'])")" --client-secret="$(python3 -c "import json;print(json.load(open('$CREDS'))['clientSecret'])")" --silent --plain)
PID=$(python3 -c "import json;print(json.load(open('$CREDS'))['projectId'])")
cd "$(dirname "$0")/.."
exec infisical run --token="$TOK" --projectId="$PID" --env=prod --silent -- python3 -m intake.poller "$@"
