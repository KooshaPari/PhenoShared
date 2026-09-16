#!/usr/bin/env bash
# Serve Qwen3.5-9B via vLLM on :30100 (Ampere/sm86 build).
#
# Rationale (from job_config.pheno-harness.qwen.yaml header):
#   sglang-kernel 0.4.x ships only sm90/sm100 wheels and drops Ampere/sm86
#   (the RTX 3090 Ti). vLLM ships Ampere wheels on the modern torch stack,
#   so Qwen3.5-9B must be served with vLLM.
#
# Invoked by tb2-30100-vllm.service (systemd). Run manually for debug:
#   bash serving/serve.sh
set -euo pipefail

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-30100}"
MODEL_PATH="${MODEL_PATH:-/home/kooshapari/models/Qwen3.5-9B}"
VLLM_PY="${VLLM_PY:-/home/kooshapari/mambaforge/envs/vllm-ampere/bin/python}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_HOME="${HF_HOME:-/home/kooshapari/.cache/huggingface}"
export LD_LIBRARY_PATH="/usr/lib/wsl/lib:/usr/local/cuda-13.3/lib64:${LD_LIBRARY_PATH:-}"

exec "$VLLM_PY" -m vllm.entrypoints.openai.api_server \
  --model "$MODEL_PATH" \
  --host "$HOST" \
  --port "$PORT" \
  --trust-remote-code \
  --gpu-memory-utilization 0.88 \
  --max-model-len 8192 \
  --tensor-parallel-size 1