# Reproduction contract — Round 9 local Qwen3.5-0.8B probe

This file documents the *exact* command sequence that reproduces the
`bench/results/2026-07-04/local_qwen35_08b_probe/` manifest end-to-end. After
the gated install runs, the actual values will be filled in; the structure is
fixed.

## Step 1 — Confirm WSL state

```bash
wsl -d Ubuntu-22.04 -- echo "alive"
wsl -d Ubuntu-22.04 -- nvidia-smi | head -20
```

Expect: `3090 Ti` reachable, CUDA 13.1, ~22 GB VRAM free.

## Step 2 — Start SGLang on WSL `:8000`

```bash
wsl -d Ubuntu-22.04 -- bash -lc "source /home/koosh/pheno-serve-venv/bin/activate && \
    python -m sglang.launch_server \
        --model /mnt/d/koosh/pheno-harness/state/model_cache/qwen35-0.8b \
        --port 8000 --host 0.0.0.0 --mem-fraction-static 0.85 \
        --speculative-algorithm EAGLE3 --speculative-draft-model-path /dev/null"
```

Expect: `INFO: Started server process`, `INFO: 127.0.0.1:8000` listening.

## Step 3 — Start vLLM on WSL `:8001`

```bash
wsl -d Ubuntu-22.04 -- bash -lc "source /home/koosh/pheno-serve-venv/bin/activate && \
    python -m vllm.entrypoints.openai.api_server \
        --model /mnt/d/koosh/pheno-harness/state/model_cache/qwen35-0.8b \
        --port 8001 --host 0.0.0.0 --gpu-memory-utilization 0.85"
```

Expect: `INFO: Started server process`, `INFO: 127.0.0.1:8001` listening.

## Step 4 — Bridge WSL → Windows host via netsh portproxy

```powershell
$wsl_ip = (wsl -d Ubuntu-22.04 -- bash -c "hostname -I").Trim().Split()[0]
netsh interface portproxy add v4tov4 listenport=8000 listenaddress=127.0.0.1 connectport=8000 connectaddress=$wsl_ip
netsh interface portproxy add v4tov4 listenport=8001 listenaddress=127.0.0.1 connectport=8001 connectaddress=$wsl_ip
```

## Step 5 — Update `pheno_serve.yaml`

```yaml
local/qwen35-08b:
  engine: sglang
  base_url: http://127.0.0.1:8000/v1
local/qwen35-08b-vllm:
  engine: vllm
  base_url: http://127.0.0.1:8001/v1
```

## Step 6 — Restart pheno-serve-dev

```powershell
powershell -NoProfile -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Id -eq 458020 } | ForEach-Object { Stop-Process -Id $_.Id -Force }; Start-Sleep 1; & C:\Python313\python.exe -u -m pheno.serve.server --config C:\Users\koosh\pheno-harness\config\pheno_serve.yaml"
```

## Step 7 — Run probes

```bash
set PYTHONPATH=C:\Users\koosh\pheno-harness
python scripts\perf_probe.py --base-url http://127.0.0.1:21080 --model local/qwen35-08b \
    --fixture bench\fixtures\qwen35_smoke\tasks.jsonl \
    --output bench\results\2026-07-04\local_qwen35_08b_probe\sglang_batch1.json \
    --batch-size 1 --engine-label sglang_batch1

python scripts\perf_probe.py --base-url http://127.0.0.1:21080 --model local/qwen35-08b-vllm \
    --fixture bench\fixtures\qwen35_smoke\tasks.jsonl \
    --output bench\results\2026-07-04\local_qwen35_08b_probe\vllm_batch1.json \
    --batch-size 1 --engine-label vllm_batch1

python scripts\specdec_trial.py --base-url http://127.0.0.1:21080 --model local/qwen35-08b \
    --output-dir bench\results\2026-07-04\local_qwen35_08b_probe\ --engine-label sglang

python scripts\specdec_trial.py --base-url http://127.0.0.1:21080 --model local/qwen35-08b-vllm \
    --output-dir bench\results\2026-07-04\local_qwen35_08b_probe\ --engine-label vllm
```

## Step 8 — GPU memory trace

```bash
wsl -d Ubuntu-22.04 -- nvidia-smi dmon -s pucm -c 30 > \
    bench/results/2026-07-04/local_qwen35_08b_probe/gpu_mem_dtrace.txt
```

Run this in parallel with the probes (start it before step 7).

## Step 9 — Manifest emission

```bash
python scripts\emit_probe_manifest.py \
    --input bench\results\2026-07-04\local_qwen35_08b_probe\ \
    --output bench\results\2026-07-04\local_qwen35_08b_probe\MANIFEST.md
```

Generates the final consolidated manifest at `MANIFEST.md` in the same
directory. (Writer script will be added in the post-install round.)

## Total wall time

Approximately 40 minutes from cold start (already-budgeted per round-9 plan §"Updated plan").
