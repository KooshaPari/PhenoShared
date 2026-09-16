# Round 9 Status — 2026-07-04

Single source of truth for round-9 state. Anything that
contradicts this file is stale.

## Round-9 in one paragraph

We drafted two bootstrap scripts (`install_wsl_pheno_serve.sh`
+ `install_wsl_pheno_serve.ps1`) that would install
SGLang 0.5.14 + vLLM 0.24.0 + torch-cu130 inside WSL2 Ubuntu-22.04
to bring up `Qwen3.5-0.8B` on the GPU. We confirmed GPU
passthrough is alive (WSL2 libcuda pre-staged, driver 591.86),
SGLang/vLLM publish only Linux wheels (no Windows wheels), and
py3.13 on Windows has torch-cpu only (no GPU runtime). The
scripts are on disk but the install is gated on user sign-off.

## What is genuinely DONE on disk

| Path | Purpose |
|---|---|
| `pheno-harness/scripts/install_wsl_pheno_serve.sh` | WSL bootstrap script: apt + python (3.14→3.13 fallback) + venv + torch-cu130 + sglang 0.5.14 + vllm 0.24.0 + cuda verify |
| `pheno-harness/scripts/install_wsl_pheno_serve.ps1` | Windows-side wrapper: one-shot HF_TOKEN via `$args[0]`, calls into WSL, heartbeat log to `bench/results/2026-07-04/_wsl_install_heartbeat.json` |

## What is PENDING (gated on user sign-off)

All of these share a single gate: the user has not said "go"
on the install. Recommended defaults if user says "go with
defaults" without picking each axis:

| Axis | Default | Why |
|---|---|---|
| WSL2 distro | Ubuntu-22.04 | Pre-registered, longest NVIDIA-WSL production record, matches SGLang/vLLM CI |
| Python in WSL | 3.13 regular | 3.14 free-thread not in 22.04's apt; pyenv + source build adds ≈ +10 min and free-thread wheels on cu130 not confirmed |
| Disk budget | ~10 GB writes | Engine wheels (6 GB) + 1.7 GB weights + caches |
| Wall time | ~30 min | apt + torch + sglang + vllm + HF download + engine warm-up |
| Cloud spend | $0 | All compute local |

### Numbered execution plan (locked on disk, gated on sign-off)

1. `wsl -d Ubuntu-22.04 -- bash -lc "apt update && apt install -y python3.13-venv python3-pip"`
2. `python3.13 -m venv /home/koosh/pheno-serve-venv`
3. `. pheno-serve-venv/bin/activate && pip install --upgrade pip`
4. `pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu130`
5. `pip install sglang==0.5.14 vllm==0.24.0 huggingface_hub`
6. `python -c "import torch; assert torch.cuda.is_available()"` (gate)
7. `huggingface-cli download Qwen/Qwen3.5-0.8B --local-dir /mnt/d/koosh/pheno-harness/state/model_cache/qwen35-0.8b`
8. SGLang on WSL `:8000`: `python -m sglang.launch_server --model-path /mnt/d/.../qwen35-0.8b --port 8000 --host 0.0.0.0 --mem-fraction-static 0.85`
9. vLLM on WSL `:8001`: `python -m vllm.entrypoints.openai.api_server --model /mnt/d/.../qwen35-0.8b --port 8001 --host 0.0.0.0 --gpu-memory-utilization 0.85`
10. Windows `netsh interface portproxy add v4tov4 listenport=8000 listenaddress=127.0.0.1 connectport=8000 connectaddress=$($(wsl hostname -I).Trim().Split()[0])` (also :8001)
11. Update `pheno_serve.yaml`: `local/qwen35-08b.engine: llama_cpp → sglang`, `base_url: http://127.0.0.1:8080/v1 → http://127.0.0.1:8000/v1`
12. Restart `pheno-serve-dev` (PID 458020); smoke + probe
13. TTFT + tokens/sec probe at batch=1+4 on both SGLang + vLLM against a 16-task smoke fixture
14. Spec-dec trial: DFlash via SGLang SpecForge, EAGLE-3 via vLLM, MTP via vLLM, N-gram fallback
15. Emit full reproducibility manifest to `bench/results/2026-07-04/local_qwen35_08b_probe/MANIFEST.md`

## What is genuinely VERIFIED (not pending)

- **WSL2 GPU passthrough**: `libcuda.so` + 17 NVIDIA libs pre-staged at `/usr/lib/wsl/lib/` (driver 591.86, CUDA 13.1).
- **`Ubuntu-22.04` WSL2 distro is RUNNING** (was Stopped before round-9 probes; probe side-effect started it).
- **PyPI wheel matrix**: `sglang==0.5.14` and `vllm==0.24.0` publish **only Linux wheels** — Windows path is dead, WSL2 is the only option.
- **Locked shortlist (ADR 0005)**: 7 cloud baselines + 3 self-hosted, Granite-4.0 Micro dropped (2026-07-04), recency cutoff 2026-03-01 enforced.
- **Spec-dec zoo** (research-watchlist, not yet validated): DFlash (SGLang SpecForge), EAGLE-3, P-EAGLE, MTP, JetSpec, DDTree, SSD, latent-MAS, REAP, NVFP4, TQ+, q4/q5/q8 KV-cache.
- **Cloud spend**: $0 across all round-9 work.

## Live running processes (untouched this round)

- `pheno-serve-dev` PID 458020 still listening on `127.0.0.1:21080` — proxy fine, config still points at `llama_cpp` upstream `:8080`.
- `Ubuntu-22.04` WSL2 distro is **RUNNING**.
- 3090 Ti idle, ~22 GB VRAM free.

## Diagnostic artifacts

| File | Reading |
|---|---|
| `bench/results/2026-07-04/_wsl_status.txt` | Default=Ubuntu-22.04, default version=2 |
| `bench/results/2026-07-04/_wsl_list_now.txt` | Ubuntu-22.04 RUNNING (was Stopped) |
| `bench/results/2026-07-04/_wsl_drv_check.txt` | 18 NVIDIA libs in C:\Windows\System32\lxss\lib\, ~400 MB |
| `bench/results/2026-07-04/_wsl_nvidia_dev.txt` | libcuda.so + 17 NVIDIA libs pre-staged at /usr/lib/wsl/lib/ |
| `bench/results/2026-07-04/_engine_smoke.out` | py3.13 baseline: torch 2.6.0+cpu (CPU only), sglang 0.5.2, vllm 0.20.0 |
| `bench/results/2026-07-04/_pypi_probe.out` | SGLang 0.5.14 + vLLM 0.24.0 publish Linux-only wheels |

## Honest self-critique (capture rule, per ADR 0004)

1. **Round 7 wrong default**: I picked ik/llama.cpp/MLX as engine primaries
   even though the repo's own `config/inference_runners.yaml` and
   `config/decode_acceleration_matrix.yaml` already encode SGLang primary
   + vLLM secondary. User pushback corrected this in round 8.
2. **Round 8 wrong assumption**: I assumed SGLang/vLLM Windows wheels might
   exist or that the GPU was unreachable from Windows. PyPI scan and
   WSL probe corrected both.
3. **Multiple closures**: I've repeated "DONE / PENDING" verbatim for the
   last several turns without making forward progress. The work that
   needed sign-off was the same throughout; the docs accumulated as
   repetition. This file is the reset.

## Next-action decision

If you say "**go**" or "**go with defaults**" → execute the 15-step
plan above in one batch with heartbeat logs to
`bench/results/2026-07-04/_wsl_install_heartbeat.json` and the
final manifest to
`bench/results/2026-07-04/local_qwen35_08b_probe/MANIFEST.md`.

If you say "**stop**" → leave this state on disk; pheno-serve-dev
PID 458020 stays alive on `:21080`; no further action this round.

If you want a different path (Ubuntu-24.04, 3.14 free-thread
build, doc-only round, different model, etc.) → tell me.