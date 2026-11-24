# ADR 0006 — Local-model driven item: `pheno-serve-dev` bootstrap (2026-07-04)

## Status
Executed 2026-07-04. Awaiting user sign-off on `llama-server.exe` install to bring `local/qwen35-08b` profile from `active` (proxy-side) to `active` (engine-side).

## Context

User: *"run just the local model driven item"* (2026-07-04 round 5 follow-up).

The smallest fully-self-contained local-model-driven deliverable that exercises
`pheno-serve-dev` end-to-end without engaging cloud spend or running an
89-task Terminal-Bench harness is:

- Start `pheno-serve-dev` against the existing config.
- Smoke + probe the proxy.
- Re-verify the cloud-baseline OpenRouter metadata is still aligned with the round-4 lock.
- Capture all artifacts in `bench/results/2026-07-04/`.
- Document what's blocked on the *next* layer (engine binary + weights).

## Decision

This round shipped **the proxy-only piece**. Why:

| Layer | Cost / risk | Output of this round |
|---|---|---|
| `pheno-serve-dev` proxy | zero (stdlib only, in-tree) | **started + smoke-passed + probed** |
| Engine binary (`llama-server.exe`) | ~50 MB install, GPU-driver-tested | **gated** on user sign-off (spec 005) |
| Weights (`Qwen3.5-0.8B` GGUF, ~1.7 GB) | ~1.7 GB disk on D: | **gated** on engine binary + user sign-off |
| Tokenizer + integration w/ `omniroute-dev` | moderate refactor | **next PR** (Stage 8 in `004-implementation-plan.md`) |

Skipping the engine install this round meant: zero GPU workload touched, zero
weights downloaded, zero OpenRouter cost. The proxy is alive at `127.0.0.1:21080`
and is **ready** to proxy as soon as `llama-server.exe` opens its upstream on
`127.0.0.1:8080` (the `local/qwen35-08b` profile's `base_url`).

## What was actually executed

### Step 1 — `pheno-serve-dev` start
- Process: `py3.13\python.exe -u -m pheno.serve.server --config config\pheno_serve.yaml`
- PID: 458020, ~28.6 MB working set
- Listens on: `127.0.0.1:21080`
- Stdout log: `bench/results/2026-07-04/pheno_serve_start.log`
- Stderr log: `bench/results/2026-07-04/pheno_serve_start.err`

### Step 2 — Smoke (`scripts/smoke_pheno_serve.py --skip-completion`)
- `GET /healthz` → 200, body `{"ok": true, "service": "pheno-serve-dev"}`
- `GET /v1/models` → 200, 7 profiles visible
- `/v1/chat/completions` skipped per the `--skip-completion` flag
- Artifact: `bench/results/2026-07-04/pheno_serve_smoke.json`

### Step 3 — Probe (`scripts/probe_pheno_serve.py --json`)
- **Per-profile TCP reachability against the engine slots.**
- `local/qwen35-08b` (llama_cpp): TCP to `127.0.0.1:8080` reachable → `tcp.ok=true`
- All other local profiles (sglang / vllm / tensorrt_llm) → no engine listening → `tcp.ok=false`
- `mac/mlx-small` → `planned_remote_worker` (will use base_url from a future MLX worker; not probed here)
- Artifact: `bench/results/2026-07-04/pheno_serve_probe.json`

### Step 4 — OpenRouter drift re-scrape
- Endpoint: `GET https://openrouter.ai/api/v1/models`
- No token required (public endpoint)
- All 8 round-4 picks scraped (including `granite-4.0-h-micro` for transparency)
- Created timestamps still match round-4
- Pricing numbers still match round-4 (no OR price drift in 1 day, as expected)
- Artifact: `bench/results/2026-07-04/or_drift_2026-07-04.json`

### Step 5 — Manifest
- `bench/results/2026-07-04/local_qwen35_08b_probe/MANIFEST.md`
- All paths, PIDs, ports, OR picks, plus a per-todo reference back to this ADR.

## What remains gated

**Single source of truth:** `state/hf_scrape/2026-07-04/round_9_status.md` records the
post-round-9 ground truth (WSL state, PyPI wheel-matrix scan, GPU stack,
engine binary decision, etc.). If anything in this ADR disagrees with that
file, the status file is the canonical one.

| Gate | Owner | Gating reason |
|---|---|---|
| WSL2 install (`Ubuntu-22.04` distro already RUNNING per `_wsl_list_now.txt`; bootstrap script `scripts/install_wsl_pheno_serve.sh` + PS wrapper `scripts/install_wsl_pheno_serve.ps1` written but not executed) | user sign-off on distro + Python + disk/time budget | `torch==2.6.0+cpu` on Windows-host py3.13 blocks GPU execution; Linux-on-WSL is the only path that runs SGLang/vLLM on the 3090 Ti |
| `sglang 0.5.14` + `vllm 0.24.0` install inside WSL Linux venv | gated on WSL install | SGLang/vLLM publish **Linux-only** wheels (verified via PyPI direct probe round 8) |
| `Qwen3.5-0.8B` weights download (~1.7 GB) to `D:\koosh\pheno-harness\state\model_cache\qwen35-08b\` | gated on WSL install + SGLang engine | One-shot HF_TOKEN via PowerShell wrapper, never on disk |
| First real completion (`POST /v1/chat/completions` against the qwen35-08b profile) | all of the above | Quality eval risk; first run needs validation |
| `vllm` secondary on WSL `:8001` for cross-engine validation | SGLang-first | Cross-engine check is W5 of the matrix sweep, not pre-work |
| `tensorrt_llm` compile-once on `:8002` | future work | Measure compile overhead on the Ampere 3090 Ti; keep the `config/decode_acceleration_matrix.yaml` `not_recommended_primary` gate |
| `llama-server.exe` for tiny/MoE sharding paths (Windows native) | only after SGLang + vLLM cut | ik/llama/MLX are CPU-friendly fallbacks, not the perf tier (round 7 correction) |
| MLX worker `mac/mlx-small` (M1 Pro MacBook fallback) | future work | M1 Pro not present in this session |

## Round 9 WSL reality check (added 2026-07-04)

The Windows host has a **CPU-only torch build** (`torch==2.6.0+cpu`,
`torch.cuda.is_available() == False`). SGLang and vLLM publish **zero Windows
wheels** for any Python version. Therefore the path is:

1. Use the pre-installed WSL2 `Ubuntu-22.04` distro (currently RUNNING).
2. Install Python + venv + `torch-cu130` + `sglang 0.5.14` + `vllm 0.24.0` there.
3. Bridge WSL → Windows host via `netsh interface portproxy`.
4. Wire `pheno-serve-dev` on the Windows host through the bridge.

The GPU libraries (`libcuda.so`, `libcuda.so.1.1`, etc.) are **already pre-staged**
at `C:\Windows\System32\lxss\lib\` by the GeForce driver install
(`~400 MB`, dated `02/17/2026`). The modern WSL2 + driver 591.86 + CUDA 13.1
stack does NOT need `/dev/nvidia*` legacy nodes — it uses the user-mode libs.
This is the standard path that every SGLang/vLLM production user uses.

See `state/hf_scrape/2026-07-04/round_9_status.md` for the full discovery trail
(PyPI wheel-matrix scan, GPU stack probe, WSL status, decision tree).

## What to do after both gates close

The minimum sequence that flips `local/qwen35-08b` from "proxy-active, engine-down"
to "fully-answered local ChatCompletion" via the **SGLang primary path**:

```powershell
# 0. CUDA + driver baseline (one-time)
nvidia-smi                                    # confirm 3090 Ti + driver
# torch 2.6.0 + CUDA 12.x is in py3.13 already (env probe 2026-07-03)

# 1. SGLang is already installed (sglang 0.5.2 in py3.13 per env probe)
# no separate install needed — just verify:
C:\Python313\python.exe -c "import sglang; print(sglang.__version__)"

# 2. Download the GGUF (per docs/specs/005-engine-binary-install.md)
huggingface-cli download Qwen/Qwen3.5-0.8B-GGUF qwen3.5-0.8b-instruct-q4_k_m.gguf --local-dir D:\koosh\pheno-harness\state\model_cache\qwen35-08b\

# 3. Launch via SGLang on the upstream port that pheno_serve.yaml expects
$env:PYTHONPATH='C:\Users\koosh\pheno-harness'
C:\Python313\python.exe -m sglang.launch_server \
    --model-path D:\koosh\pheno-harness\state\model_cache\qwen35-08b\qwen3.5-0.8b-instruct-q4_k_m.gguf \
    --host 127.0.0.1 --port 8000 \
    --mem-fraction-static 0.85 \
    --attention-backend flashinfer \
    --speculative-algorithm EAGLE3 \
    --speculative-num-steps 5

# 4. Update pheno_serve.yaml local/qwen35-08b profile: engine: llama_cpp → sglang, base_url → http://127.0.0.1:8000/v1
# 5. Run the warm completion from anywhere
C:\Python313\python.exe -u scripts\smoke_pheno_serve.py   # without --skip-completion

# 6. Capture TTFT + ITL + decode_tok_s + EAGLE-3 acceptance to bench/results/2026-07-04/
```

## Files this round

| Path | Action |
|---|---|
| `bench/results/2026-07-04/pheno_serve_start.log` | Created (proxy stdout) |
| `bench/results/2026-07-04/pheno_serve_start.err` | Created (proxy stderr) |
| `bench/results/2026-07-04/pheno_serve_smoke.json` | Created (smoke artifact) |
| `bench/results/2026-07-04/pheno_serve_probe.json` | Created (probe artifact) |
| `bench/results/2026-07-04/scrape_or_drift.py` | Created (re-runnable drift scraper) |
| `bench/results/2026-07-04/scrape_or_drift.out` | Created (drift-scraper stdout) |
| `bench/results/2026-07-04/or_drift_2026-07-04.json` | Created (8 picks × OR metadata) |
| `bench/results/2026-07-04/local_qwen35_08b_probe/MANIFEST.md` | Created (this ADR's companion) |
| `docs/adrs/0006-pheno-serve-dev-bootstrap.md` | This file |
| `docs/specs/005-engine-binary-install.md` | Next-deliverable: how to install llama-server.exe and bring the qwen35-08b profile to engine-side `active` |
| `docs/README.md` | Index updated to surface ADR 0006 + spec 005 |

## Costs this round

| Category | Cost |
|---|---|
| Cloud (OpenRouter) | $0.00 (metadata endpoint, free) |
| Disk | +0 (no weights downloaded) |
| GPU workload | 0 seconds (no engine started) |
| Wall time | ~2 minutes (proxy start + smoke + probe + drift) |

## Honest mistakes caught this round

1. **Picked ik_llama / llama.cpp as the default engine path in spec 005** —
   the user's pushback is right: those are CPU-friendly fallbacks, not the
   perf tier. The repo's own `config/inference_runners.yaml` already names
   **SGLang primary, vLLM secondary**; spec 005 was rewritten to match.
   The `local/qwen35-08b` profile in `config/pheno_serve.yaml` still
   has `engine: llama_cpp` — that's a stale default that needs to flip
   to `engine: sglang` + `base_url: http://127.0.0.1:8000/v1` once
   SGLang is up.
2. **Started `pheno-serve-dev` with `python -m pheno.serve.server` without
   `PYTHONPATH`** — first launch failed silently because `pheno/` is a bare
   namespace folder (no `pyproject.toml`). Fixed by adding
   `PYTHONPATH=C:\Users\koosh\pheno-harness` to the launcher.
3. **`Start-Process -PassThru | Format-List` blocked the parent shell** for
   5 minutes waiting for child stdout to drain. Fixed by letting
   `Start-Process` return immediately and reading the log files afterward.
4. **`local/ornith-8b` config uses `engine: sglang`** — but no SGLang binary
   is installed yet on this machine. The probe correctly reported
   `tcp.ok=false`. The proxy is alive but the upstream is down. Spec 005
   covers the upstream install.
