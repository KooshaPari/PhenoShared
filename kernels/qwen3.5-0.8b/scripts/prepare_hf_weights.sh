#!/usr/bin/env bash
# prepare_hf_weights.sh — Populate the Qwen3.5 0.8B HuggingFace safetensors
# checkpoint on disk and verify it can be loaded.
#
# Usage:
#   bash scripts/prepare_hf_weights.sh                  # default cache dir
#   bash scripts/prepare_hf_weights.sh /path/to/hf-dir   # explicit dir
#   HF_REPO=Qwen/Qwen3.5-0.8B bash scripts/prepare_hf_weights.sh
#
# Default cache dir: kernels/qwen3.5-0.8b/weights/build/hf-cache
# Default HF repo:   Qwen/Qwen3.5-0.8B
#
# After this script finishes, downstream tools can use the weights via:
#   python3 -m weights inspect
#   python3 -m weights dump-blob weights/build/weights.bin
#   python3 -m weights sample "The capital of France is"
#
# Prerequisites:
#   - python3 with huggingface_hub installed
#   - mlx, safetensors, tokenizers for the inspect/sample subcommands

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
WEIGHTS_DIR="${KERNEL_DIR}/weights"

# Args / env
HF_DIR="${1:-${WEIGHTS_DIR}/build/hf-cache}"
HF_REPO="${HF_REPO:-Qwen/Qwen3.5-0.8B}"
PY="${PYTHON:-python3}"

mkdir -p "${HF_DIR}"

log()  { printf "[prepare_hf] %s\n" "$*" >&2; }
fail() { printf "[prepare_hf] ERROR: %s\n" "$*" >&2; exit 1; }

# --- 1. Make sure huggingface_hub is installed --------------------------------
if ! "${PY}" -c "import huggingface_hub" 2>/dev/null; then
    log "installing huggingface_hub"
    "${PY}" -m pip install --quiet "huggingface_hub>=0.20"
fi

# --- 2. Make sure safetensors is installed (for the inspect path) -------------
if ! "${PY}" -c "import safetensors" 2>/dev/null; then
    log "installing safetensors"
    "${PY}" -m pip install --quiet safetensors
fi

# --- 3. Make sure tokenizers is installed (for the sample path) ----------------
if ! "${PY}" -c "import tokenizers" 2>/dev/null; then
    log "installing tokenizers"
    "${PY}" -m pip install --quiet tokenizers
fi

# --- 4. Make sure mlx is installed (for sample / inspect) ---------------------
if ! "${PY}" -c "import mlx.core" 2>/dev/null; then
    log "installing mlx"
    "${PY}" -m pip install --quiet mlx
fi

# --- 5. Trigger the download ---------------------------------------------------
log "downloading ${HF_REPO} -> ${HF_DIR}"
"${PY}" -m weights --hf-dir "${HF_DIR}" --repo "${HF_REPO}" download
log "download complete"

# --- 6. Verify load + dump the blob -------------------------------------------
log "verifying weights load"
"${PY}" -m weights --hf-dir "${HF_DIR}" inspect

log "writing flat bf16 blob"
"${PY}" -m weights --hf-dir "${HF_DIR}" dump-blob "${WEIGHTS_DIR}/build/weights.bin"

log "DONE. Files:"
ls -lh "${HF_DIR}" "${WEIGHTS_DIR}/build" 2>/dev/null || true
exit 0