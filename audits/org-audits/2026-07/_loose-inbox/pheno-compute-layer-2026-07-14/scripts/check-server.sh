#!/bin/bash
#==========================================
# Check LLM inference server health for desktop
#==========================================

set -e

# Config (can be overridden by env)
DESKTOP_URL="${DESKTOP_URL:-http://100.96.135.160:8080/v1}"
TAILSCALE_HOST="${TAILSCALE_HOST:-100.96.135.160}"
PORT="${PORT:-8080}"
COMPUTE_HOST="${COMPUTE_HOST:-desk}"
TIMEOUT=5

# Derived endpoint
ENDPOINT="${DESKTOP_URL}"
if [[ ! "$ENDPOINT" == *"/v1" ]]; then
    ENDPOINT="http://${TAILSCALE_HOST}:${PORT}/v1"
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_detail() { echo -e "${BLUE}[DETAIL]${NC} $1"; }

check_http() {
    local url="$1"
    local response
    if response=$(curl -fsS --max-time "$TIMEOUT" "$url" 2>/dev/null); then
        echo "$response"
        return 0
    fi
    return 1
}

# Resolve endpoint from host config and verify server process on desktop
log_info "Checking inference endpoint: $ENDPOINT"

HTTP_OK=false
if response=$(check_http "$ENDPOINT/models"); then
    HTTP_OK=true
    log_info "Server is reachable"
    echo "  /models response received"

    # Parse quick status from models payload if possible
    model_count=$(python3 - <<'PY' <<<"$response"
import json, sys
try:
    data = json.load(sys.stdin)
    models = data.get("data") or []
    print(len(models))
except Exception:
    print("-1")
PY
)
    if [[ "$model_count" == "-1" ]]; then
        log_warn "Could not parse /models JSON payload"
    else
        log_info "Available models reported: $model_count"
        if [[ "$model_count" != "0" ]]; then
            echo "$response" | python3 - <<'PY'
import sys, json
payload = json.load(sys.stdin)
for item in payload.get("data", []):
    mid = item.get("id", "")
    if mid:
        print(f"  - {mid}")
PY
        fi
    fi
else
    log_warn "Server not reachable on /models"
fi

log_info "Checking remote process on $COMPUTE_HOST (vLLM / SGLang / llama-server)"
if remote=$(ssh "$COMPUTE_HOST" "ps -ef | grep -E 'vllm|sglang|llama-server' | grep -v grep" 2>/dev/null); then
    log_info "Server process found"
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        log_detail "$line"
    done <<<"$remote"
else
    log_warn "No recognized server process found via SSH"
fi

if $HTTP_OK; then
    echo
    log_info "LLM endpoint is UP"
    echo "  URL: $ENDPOINT"
    exit 0
else
    echo
    log_error "LLM endpoint is not reachable"
    echo "  URL: $ENDPOINT"
    echo "  Use scripts/start-llm-server.sh to start inference service"
    exit 2
fi