#!/bin/bash
#==========================================
# Start LLM inference server on desktop WSL
# Binds to 0.0.0.0:8080 for Tailscale access
#==========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Configuration - sourced from config.env
DESKTOP_HOST="${DESKTOP_HOST:-desk}"
TAILSCALE_HOST="${TAILSCALE_HOST:-100.96.135.160}"
PORT="${PORT:-8080}"
WSL_USER="${WSL_USER:-kooshapari}"

# Model defaults
DEFAULT_MODEL_KEY="granite_4_1_8b"
DEFAULT_QUANT="${DEFAULT_QUANT:-Q4_K_M}"
MODELS_DIR="${MODELS_DIR:-/home/kooshapari/llm-models}"
LOG_DIR="${LOG_DIR:-$HOME/llm-server}"

# Backend selection
SERVICE_BACKEND="${SERVICE_BACKEND:-vllm}"
LLAMA_SERVER="${LLAMA_SERVER:-/home/kooshapari/llama.cpp/llama-b9010/llama-server}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

usage() {
    cat << EOF
start-llm-server.sh - Start LLM inference server on desktop WSL

Usage: $0 [options] [model-key]

Options:
  --backend <backend>   Backend: vllm, llama.cpp, sglang (default: vllm)
  --model <key>        Model key (default: granite_4_1_8b)
  --port <port>        Port (default: 8080)
  --model-path <path>  Explicit model GGUF path
  --dry-run            Show command without executing
  -h, --help           Show this help

Model Keys:
  granite_4_1_8b       IBM Granite 4.1 8B IQ4_NL (4.8GB) - BEST coding
  qwen3_6_35b_a3b_iq2  Qwen3.6 35B MoE UD-IQ2_M (12GB) - reasoning
  qwen3_6_28b_reap      Qwen3.6 28B REAP Q4_K_M (18GB) - REAP specialized

Examples:
  $0                           # Start Granite 4.1 8B with vLLM
  $0 --backend llama.cpp       # Start with llama.cpp server
  $0 --model qwen3_6_35b_a3b_iq2  # Start Qwen MoE
  $0 --dry-run                 # Show what would be run
EOF
}

# Parse arguments
MODEL_KEY="$DEFAULT_MODEL_KEY"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backend)
            SERVICE_BACKEND="$2"
            shift 2
            ;;
        --model)
            MODEL_KEY="$2"
            shift 2
            ;;
        --model-path)
            MODEL_PATH="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            MODEL_KEY="$1"
            shift
            ;;
    esac
done

# Build model path from model key if not provided
build_model_path() {
    local key="$1"
    local quant="${2:-$DEFAULT_QUANT}"

    case "$key" in
        granite_4_1_8b)
            echo "$MODELS_DIR/granite_4_1_8b/granite-4.1-8b-IQ4_NL.gguf"
            ;;
        granite_4_1_8b_q4)
            echo "$MODELS_DIR/granite_4_1_8b/granite-4.1-8b-Q4_K_M.gguf"
            ;;
        granite_4_1_8b_udq2)
            echo "$MODELS_DIR/granite_4_1_8b/granite-4.1-8b-UD-IQ2_M.gguf"
            ;;
        qwen3_6_35b_a3b_iq2)
            echo "$MODELS_DIR/qwen3_6_35b_a3b/Qwen3.6-35B-A3B-UD-IQ2_M.gguf"
            ;;
        qwen3_6_35b_a3b)
            echo "$MODELS_DIR/qwen3_6_35b_a3b/Qwen3.6-35B-A3B-Q4_K_M.gguf"
            ;;
        qwen3_6_28b_reap)
            echo "$MODELS_DIR/qwen3_6_28b_reap/Qwen3.6-28B-REAP.Q4_K_M.gguf"
            ;;
        *)
            echo "$MODELS_DIR/$key"
            ;;
    esac
}

if [ -z "$MODEL_PATH" ]; then
    MODEL_PATH=$(build_model_path "$MODEL_KEY")
fi

# Ensure log directory exists
LOG_FILE="$LOG_DIR/${MODEL_KEY}.log"
mkdir -p "$LOG_DIR"

# Build command based on backend
start_vllm() {
    log_info "Building vLLM start command..."
    local cmd="python -m vllm.entrypoints.openai.api_server \
        --model '$MODEL_PATH' \
        --served-model-name '$MODEL_KEY' \
        --host 0.0.0.0 \
        --port $PORT \
        --trust-remote-code \
        --gpu-memory-utilization 0.90"

    echo "$cmd"
}

start_llama_cpp() {
    log_info "Building llama.cpp server command..."
    local cmd="$LLAMA_SERVER \
        -m '$MODEL_PATH' \
        --host 0.0.0.0 \
        -p $PORT \
        -c 8192"

    echo "$cmd"
}

start_sglang() {
    log_info "Building SGLang start command..."
    local cmd="python -m sglang.launch_server \
        --model-path '$MODEL_PATH' \
        --host 0.0.0.0 \
        --port $PORT \
        --trust-remote-code"

    echo "$cmd"
}

# Determine command
case "$SERVICE_BACKEND" in
    vllm)
        SSH_CMD="ssh $DESKTOP_HOST"
        # Use WSL directly
        RUN_CMD="wsl -d Ubuntu-22.04 -e bash -c"
        COMMAND=$(start_vllm)
        ;;
    llama.cpp|llama)
        SSH_CMD="ssh $DESKTOP_HOST"
        RUN_CMD="wsl -d Ubuntu-22.04 -e bash -c"
        COMMAND=$(start_llama_cpp)
        ;;
    sglang)
        SSH_CMD="ssh $DESKTOP_HOST"
        RUN_CMD="wsl -d Ubuntu-22.04 -e bash -c"
        COMMAND=$(start_sglang)
        ;;
    *)
        log_error "Unknown backend: $SERVICE_BACKEND"
        exit 1
        ;;
esac

# Full SSH command
FULL_CMD="$SSH_CMD '$RUN_CMD \"pkill -f vllm 2>/dev/null || true; pkill -f llama-server 2>/dev/null || true; mkdir -p $LOG_DIR; $COMMAND &> $LOG_FILE &\"'"

echo ""
log_info "Start LLM Server"
echo "=================="
echo "  Backend: $SERVICE_BACKEND"
echo "  Model Key: $MODEL_KEY"
echo "  Model Path: $MODEL_PATH"
echo "  Port: $PORT"
echo "  Endpoint: http://${TAILSCALE_HOST}:${PORT}/v1"
echo "  Log File: $LOG_FILE"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_info "DRY RUN - Command that would be executed:"
    echo "$FULL_CMD"
    exit 0
fi

log_info "Stopping any existing server..."
eval "$SSH_CMD '$RUN_CMD \"pkill -f vllm 2>/dev/null; pkill -f llama-server 2>/dev/null; pkill -f sglang 2>/dev/null; echo done\"'"

log_info "Starting $SERVICE_BACKEND server..."
log_info "Command: $COMMAND"

eval "$FULL_CMD"

log_info "Server starting on port $PORT..."
log_info "Waiting 15 seconds for model to load..."
sleep 15

# Health check
log_info "Running health check..."
if curl -s --connect-timeout 5 "http://${TAILSCALE_HOST}:${PORT}/v1/models" > /dev/null 2>&1; then
    log_info "Server is running!"
    curl -s "http://${TAILSCALE_HOST}:${PORT}/v1/models" | python3 -c "
import sys, json
d = json.load(sys.stdin)
models = d.get('data', [])
for m in models:
    print(f\"  Model: {m.get('id', 'unknown')}\")
" 2>/dev/null || echo "  (model list not available)"
else
    log_warn "Server may still be loading. Check logs:"
    echo "  tail -f $LOG_FILE"
fi

echo ""
log_info "Endpoint: http://${TAILSCALE_HOST}:${PORT}/v1"
log_info "Logs: $LOG_FILE"
