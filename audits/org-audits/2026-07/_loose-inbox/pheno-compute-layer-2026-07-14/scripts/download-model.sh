#!/bin/bash
#==========================================
# OmniRoute Model Downloader
# Uses uv for Python package management
#==========================================

set -e

# Config
MODELS_DIR="${HOME}/llm-models"
HF_HUB_CACHE="${HOME}/.cache/huggingface"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
info() { echo -e "${BLUE}[STEP]${NC} $1"; }

# Model definitions - verified GGUF repos
# Format: key|org|repo|filename|quant|size_gb|description
MODELS=(
    # Granite 4.1 (IBM) - Best coding model
    "granite_4_1_8b|unsloth|granite-4.1-8b-GGUF|granite-4.1-8b-IQ4_NL.gguf|IQ4_NL|4.8|IBM Granite coding (BEST) ⭐"
    "granite_4_1_8b_q4|unsloth|granite-4.1-8b-GGUF|granite-4.1-8b-Q4_K_M.gguf|Q4_K_M|5|Granite Q4 variant"
    "granite_4_1_8b_udq2|unsloth|granite-4.1-8b-GGUF|granite-4.1-8b-UD-IQ2_M.gguf|UD-IQ2_M|3.2|Granite ultra-low mem"
    
    # Granite 4.1 Thinking variants
    "granite_4_1_8b_think|mradermacher|granite-4.1-8b-Brainstone-Thinking-i1-GGUF|Q4_K_M.gguf|Q4_K_M|5.5|Granite thinking"
    "granite_4_1_8b_stone|mradermacher|granite-4.1-8b-i1-GGUF|Q4_K_M.gguf|Q4_K_M|5|Granite i1 trained"
    
    # Qwen3.6 MoE (35B total, ~3B active)
    "qwen3_6_35b_a3b|unsloth|Qwen3.6-35B-A3B-GGUF|Qwen3.6-35B-A3B-Q4_K_M.gguf|Q4_K_M|21|MoE 35B/3B full"
    "qwen3_6_35b_a3b_iq2|unsloth|Qwen3.6-35B-A3B-GGUF|Qwen3.6-35B-A3B-UD-IQ2_M.gguf|UD-IQ2_M|12|MoE ultra-low mem ⭐"
    "qwen3_6_35b_a3b_iq4|unsloth|Qwen3.6-35B-A3B-GGUF|Qwen3.6-35B-A3B-UD-IQ4_NL.gguf|UD-IQ4_NL|9|MoE lowest mem"
    "qwen3_6_35b_a3b_iq3|unsloth|Qwen3.6-35B-A3B-GGUF|Qwen3.6-35B-A3B-UD-IQ3_S.gguf|UD-IQ3_S|15|MoE balanced low"
    
    # Qwen3.6 REAP (Router-Aware Expert Allocation)
    "qwen3_6_28b_reap|mradermacher|Qwen3.6-28B-REAP-GGUF|Qwen3.6-28B-REAP.Q4_K_M.gguf|Q4_K_M|18|REAP 28B/3B ⭐"
    "qwen3_6_28b_reap20|barozp|Qwen3.6-28B-REAP20-A3B-GGUF|Qwen3.6-28B-REAP20-A3B-Q4_K_M.gguf|Q4_K_M|18|REAP20 variant"
    
    # Qwen3.6 Reasoning Distilled
    "qwen3_6_35b_distill|mradermacher|Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-i1-GGUF|Q4_K_M.gguf|Q4_K_M|22|Claude distilled ⭐"
    "qwen3_6_35b_apex|mudler|Qwen3.6-35B-A3B-Claude-4.7-Opus-Reasoning-Distilled-APEX-GGUF|Q4_K_M.gguf|Q4_K_M|22|APEX distilled"
    
    # Qwen3.5 MoE (35B) - if we want to use it
    "qwen3_5_35b_a3b|unsloth|Qwen3.5-35B-A3B-GGUF|Qwen3.5-35B-A3B-Q4_K_M.gguf|Q4_K_M|21|Qwen3.5 MoE"
)

usage() {
    cat << EOF
OmniRoute Model Downloader
===========================

Commands:
  install <model>     Download a model
  list                List available models
  install-core        Download core models (within 1hr) ⭐
  install-reap        Download REAP variants
  install-all         Download everything
  verify <model>      Verify model files exist

CORE Models (recommended ⭐):
  granite_4_1_8b       IBM Granite coding (4.8GB) ⭐⭐⭐
  qwen3_6_35b_a3b_iq2  MoE ultra-low mem (12GB) ⭐⭐
  qwen3_6_28b_reap     REAP optimized (18GB) ⭐⭐
  qwen3_6_35b_distill  Claude distilled (22GB) ⭐⭐

REAP Variants:
  qwen3_6_28b_reap     REAP 28B/3B
  qwen3_6_28b_reap20   REAP20 (20-expert)

Examples:
  $0 install-core      # Download priority models (recommended!)
  $0 install granite_4_1_8b
  $0 install-reap
EOF
}

check_uv() {
    if ! command -v uv &> /dev/null; then
        warn "Installing uv..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.local/bin:$PATH"
    fi
}

setup_python() {
    check_uv
    if [ ! -d "${HOME}/.venv/omni" ]; then
        log "Creating Python venv..."
        uv venv "${HOME}/.venv/omni"
    fi
    source "${HOME}/.venv/omni/bin/activate"
    uv pip install huggingface-hub -q
}

get_model_info() {
    local model_name="$1"
    for entry in "${MODELS[@]}"; do
        IFS='|' read -r key org repo file quant size desc <<< "$entry"
        if [ "$key" = "$model_name" ]; then
            echo "$entry"
            return 0
        fi
    done
    return 1
}

download_model() {
    local model_name="$1"
    local info
    info=$(get_model_info "$model_name")
    
    if [ -z "$info" ]; then
        error "Unknown model: $model_name"
        return 1
    fi
    
    IFS='|' read -r key org repo file quant size desc <<< "$info"
    
    local dest_dir="${MODELS_DIR}/${key}"
    local dest_file="${dest_dir}/${file}"
    
    if [ -f "$dest_file" ]; then
        log "Model already exists: $model_name ($desc)"
        return 0
    fi
    
    info "Downloading $model_name: $desc (${size}GB)..."
    
    setup_python
    
    mkdir -p "$dest_dir"
    
    python3 -c "
from huggingface_hub import hf_hub_download
path = hf_hub_download(
    repo_id='${org}/${repo}',
    filename='${file}',
    local_dir='${dest_dir}',
    local_dir_use_symlinks=False
)
print(f'Downloaded to: {path}')
"
    
    ls -lh "$dest_dir"
}

list_models() {
    echo "Available Models:"
    echo "================"
    for entry in "${MODELS[@]}"; do
        IFS='|' read -r key org repo file quant size desc <<< "$entry"
        
        local dest_file="${MODELS_DIR}/${key}/${file}"
        if [ -f "$dest_file" ]; then
            echo -e "  ${GREEN}[INSTALLED]${NC} $key"
        else
            echo -e "  ${YELLOW}[NOT INSTALLED]${NC} $key"
        fi
        echo "    $desc (${size}GB)"
        echo "    ${org}/${repo}"
        echo ""
    done
}

install_core() {
    info "Installing CORE models (priority)..."
    echo ""
    
    # Priority order - best models first
    for model in granite_4_1_8b qwen3_6_35b_a3b_iq2 qwen3_6_28b_reap qwen3_6_35b_distill; do
        download_model "$model"
        echo ""
    done
    
    log "Core models installed!"
}

install_reap() {
    info "Installing REAP variants..."
    echo ""
    
    for model in qwen3_6_28b_reap qwen3_6_28b_reap20; do
        download_model "$model"
        echo ""
    done
    
    log "REAP models installed!"
}

verify_model() {
    local model_name="$1"
    local info
    info=$(get_model_info "$model_name")
    
    if [ -z "$info" ]; then
        error "Unknown model: $model_name"
        return 1
    fi
    
    IFS='|' read -r key org repo file quant size desc <<< "$info"
    local dest_file="${MODELS_DIR}/${key}/${file}"
    
    if [ -f "$dest_file" ]; then
        log "Verified: $model_name (${size}GB) - $(du -h "$dest_file" | cut -f1)"
    else
        error "Missing: $model_name"
    fi
}

# Main
case "${1:-}" in
    install)
        if [ -z "$2" ]; then
            error "Usage: $0 install <model>"
            exit 1
        fi
        download_model "$2"
        ;;
    list)
        list_models
        ;;
    install-core)
        install_core
        ;;
    install-reap)
        install_reap
        ;;
    install-all)
        install_core
        install_reap
        ;;
    verify)
        if [ -z "$2" ]; then
            error "Usage: $0 verify <model>"
            exit 1
        fi
        verify_model "$2"
        ;;
    *)
        usage
        ;;
esac
