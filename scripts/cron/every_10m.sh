#!/usr/bin/env bash
# Pheno-Harness — every-10-minute benchmark tick
set -euo pipefail

LOG=/tmp/pheno-cron.log
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] cron-tick start" >> "$LOG"

PHENO_ROOT="${PHENO_ROOT:-/Users/<REDACTED>/CodeProjects/Phenotype/pheno-harness}"
cd "$PHENO_ROOT" || { echo "cd failed" >> "$LOG"; exit 1; }

# Quick health-check: MLX server
if curl -sL --max-time 3 http://127.0.0.1:8765/v1/models >/dev/null 2>&1; then
    echo "[cron] MLX server OK" >> "$LOG"
else
    echo "[cron] MLX server down — starting" >> "$LOG"
    SNAP=$(ls -d /Users/<REDACTED>/.cache/huggingface/hub/models--Qwen--Qwen3.5-0.8B/snapshots/*/ | head -1)
    nohup /opt/homebrew/bin/python3.12 -m mlx_lm.server \
        --model "$SNAP" --host 127.0.0.1 --port 8765 --log-level WARNING \
        > /tmp/mlx-server-stock.log 2>&1 &
    echo "[cron] MLX server PID=$!" >> "$LOG"
fi

# Quick benchmark: 1 suite × 5 tasks × mock (fast, ~15s)
OUTDIR="$PHENO_ROOT/bench/results/cron"
mkdir -p "$OUTDIR"
timeout 30 /opt/homebrew/bin/python3.12 -m bench.comparison.stock_vs_ours \
    --adapter mock --tasks 5 --seed 42 --variants control \
    --out-dir "$OUTDIR" 2>&1 | tail -5 >> "$LOG"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] cron-tick done" >> "$LOG"
