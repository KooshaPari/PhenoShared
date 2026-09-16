#!/bin/bash
#==========================================
# llama.cpp Server Startup Script
# For WSL2 Ubuntu with NVIDIA GPU
#==========================================

set -e

# Configuration
MODEL_PATH="${MODEL_PATH:-$HOME/llm-models/Qwen3.6-35B-A3B/Qwen3.6-35B-A3B-Q4_K_M.gguf}"
PORT="${PORT:-8080}"
CTX_SIZE="${CTX_SIZE:-8192}"
GPU_LAYERS="${GPU_LAYERS:-99}"
LLAMA_SERVER="$HOME/llama.cpp/llama-server"

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date)]${NC} $1"; }

# Check GPU
log "Checking GPU..."
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# Check model exists
if [ ! -f "$MODEL_PATH" ]; then
    echo "ERROR: Model not found at $MODEL_PATH"
    echo "Download with: huggingface-cli download <repo> <file> --local-dir $(dirname $MODEL_PATH)"
    exit 1
fi

log "Model: $MODEL_PATH"
log "Port: $PORT"
log "Context: $CTX_SIZE"
log "GPU Layers: $GPU_LAYERS"

# Kill existing server on port
pkill -f "llama-server.*--port $PORT" 2>/dev/null || true
sleep 1

# Start server
log "Starting llama-server..."

$LLAMA_SERVER \
    -m "$MODEL_PATH" \
    -c $CTX_SIZE \
    -ngl $GPU_LAYERS \
    --port $PORT \
    --host 0.0.0.0 \
    --log-disable \
    2>&1 | while read line; do
        echo "[$(date)] $line"
    done
