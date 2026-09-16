# Spec 005 — Engine binary install on 3090 Ti (2026-07-04, revised 2026-07-04 round 7, **round 9 WSL**)

> **July 14 status:** this is a historical bootstrap record, not the current
> model/runtime authority. Use `config/heterogeneous_tournament.yaml`,
> `config/inference_runners.yaml`, and
> `plans/2026-07-14-usch-heterogeneous-inference-v1/MODEL_RUNTIME_MATRIX.md`
> for audited pins and admission gates. The RTX 3090 Ti is Ampere (`sm_86`),
> not Ada; any old Ada-based compile or latency estimate is non-transferable.
> Every “already installed” or build-time statement below is a July 4 historical
> observation and is unverified for the current environment; it is not launch
> authorization or evidence that a pinned runtime is present now.

> **Round 9 update (2026-07-04):** SGLang/vLLM have **no native Windows wheels**
> (verified via PyPI JSON probe — all wheels are `manylinux_x86_64`). The install
> path on Windows is therefore **WSL2 + Linux Python**, not native Windows.
> Single source of truth for the WSL/blocker state:
> `state/hf_scrape/2026-07-04/round_9_status.md`. Read that first.

## Status

Revised after user pushback: ik/llama.cpp/MLX are CPU-tier fallbacks, not the
perf tier. **SGLang primary, vLLM secondary, llama.cpp small-model fallback,
TensorRT-LLM measured third, MLX remote-worker M1 Pro only.** This matches
`config/inference_runners.yaml`, `config/decode_acceleration_matrix.yaml`, and
`config/local_model_bench_matrix.yaml` (the canonical repo truth).

The WSL bootstrap refuses to install when its backing volume has less than
50 GB free (`PHENO_WSL_MIN_FREE_GB`, default 50). C: is currently below that
threshold; move WSL storage before starting the multi-engine stack. This is
separate from the D: model-cache admission check.

Model weights and quantized artifacts use `PHENO_MODEL_CACHE_ROOT`, defaulting
to `D:\WSL\model-cache`; benchmark reports remain under the repository on C:.

The read-only relocation plan is generated with:

```powershell
powershell -File scripts\relocate_wsl_distro.ps1 `
  -Distro Ubuntu-22.04 -TargetRoot D:\WSL\Ubuntu-22.04
```

The script reports the source VHDX size and target admission. It will not
unregister/import anything unless both `-Execute` and `-ConfirmUnregister` are
provided; the export is verified with SHA256 before that destructive step.

## Why SGLang primary, vLLM secondary, llama.cpp fallback

- **`config/inference_runners.yaml`** has `sglang` as the first runner
  (port 8000), `vllm` as the second (port 8001), `llama_server` as the third
  (port 8080). The repo already pre-decided this order.
- **`config/decode_acceleration_matrix.yaml`** is the sole current authority
  for decode experiments. It requires an exact compatible base/draft pair and
  quarantines the proxy pairings that this July-4 document once proposed.
- **SGLang and vLLM** must be compared on the same admitted artifact and trace
  corpus. Cold-start, prefix-cache, chunked-prefill, and speculative-decoding
  advantages are measurements, not engine-wide assumptions.
- **TensorRT-LLM** compile time must be measured on the Ampere RTX 3090 Ti;
  estimates from Ada or Blackwell are not transferable. Only the
  LFM2.5-8B-A1B profile in this historical bootstrap lists it
  (`tensorrt_llm_compile_once`). The repo pre-marks it as
  `planned_compile_once` in `pheno_serve.yaml`. Useful for steady-state
  latency after the model is locked, **not** for early-stage evals.
- **llama.cpp** is the GGUF/portability control and may also serve admitted
  large low-bit artifacts; it is not restricted to sub-1B models.
- **oMLX/MLX** is the M1 Pro lane, with llama.cpp Metal as its cross-runtime
  control. Neither is on the 3090 Ti path.

## Tier 1: SGLang (primary, models L1, L2, L3)

**Use for:** every primary eval. `local/lfm25-8b-a1b` and `local/ornith-8b`
both already wire `engine: sglang` in `config/pheno_serve.yaml` — those
profiles are the canonical SGLang home.

| Property | Value |
|---|---|
| Engine | Current audited pin: SGLang 0.5.15.post1; verify the environment rather than assuming it is installed |
| Default port | 8000 |
| HTTP API | OpenAI-compatible `/v1/chat/completions` |
| Per-model command | `python -m sglang.launch_server --model-path <repo> --host 127.0.0.1 --port 8000 --mem-fraction-static 0.85` |
| Cold start (24 GB) | Historical estimate only; remeasure per admitted artifact |
| Continuous batching | on by default |
| Chunked prefill | on by default |
| Prefix cache | on by default (LRU, hash-keyed) |
| Spec-dec on SGLang | EAGLE-2, EAGLE-3, N-gram, draft-model (MTP, DFlash via `--speculative-draft-model-path`) |
| Custom CUDA kernels | triton kernels (FP8, INT4, etc.) — needed for the larger T2/T3 sweeps |
| Disk | ~5 GB (engine + cache) |
| Build time | none (already installed) |

### Install commands

```powershell
# Already in py3.13; verify version
C:\Python313\python.exe -c "import sglang; print('sglang:', sglang.__version__)"

# Start a 0.8 B Qwen3.5 (drafter tier) on SGLang
$env:PYTHONPATH='C:\Users\koosh\pheno-harness'
$env:HF_TOKEN = (Read-Host -AsSecureString | ConvertFrom-SecureString)   # optional, gated

# SGLang needs the HF safetensors for Qwen3.5-0.8B, not the GGUF.
# Note: the qwen35-08b profile currently uses engine=llama_cpp; we'll override at launch.
python -m sglang.launch_server `
  --model-path Qwen/Qwen3.5-0.8B `
  --host 127.0.0.1 --port 8000 `
  --mem-fraction-static 0.85 `
  --enable-prefix-caching `
  --enable-chunked-prefill
```

## Tier 2: vLLM (secondary, all models with vLLM profile)

**Use for:** cross-checking SGLang numbers, plus the spec-dec sweeps
(EAGLE-3, DFlash) that `config/decode_acceleration_matrix.yaml` lists.

| Property | Value |
|---|---|
| Engine | Current audited pin: vLLM 0.25.1; verify the environment rather than assuming it is installed |
| Default port | 8001 |
| HTTP API | OpenAI-compatible `/v1/chat/completions` |
| Per-model command | `python -m vllm.entrypoints.openai.api_server --model <repo> --host 127.0.0.1 --port 8001` |
| Cold start (24 GB) | Historical estimate only; remeasure per admitted artifact |
| Continuous batching | on by default |
| Chunked prefill | on by default |
| Prefix cache | on by default (LRU, hash-keyed) |
| Spec-dec on vLLM | EAGLE-2, EAGLE-3, n-gram, MTP, suffix, Speculators library, MLP-draft |
| Custom CUDA kernels | triton + custom (FlashAttention, etc.) — full support |
| Disk | ~5 GB (engine + cache) |
| Build time | none (already installed) |

### Install commands

```powershell
# Already in py3.13
C:\Python313\python.exe -c "import vllm; print('vllm:', vllm.__version__)"

# Start Qwen3.5-0.8B on vLLM
$env:PYTHONPATH='C:\Users\koosh\pheno-harness'
python -m vllm.entrypoints.openai.api_server `
  --model Qwen/Qwen3.5-0.8B `
  --host 127.0.0.1 --port 8001 `
  --max-model-len 8192 `
  --enable-prefix-caching `
  --enable-chunked-prefill `
  --gpu-memory-utilization 0.85
```

## Tier 3: llama.cpp (fallback, `local/qwen35-08b` only)

**Use for:** the smallest 0.8 B model when we need a GGUF-friendly path
(M1 Pro worker, low-spec worker nodes, GGUF-based drafter, when SGLang /
vLLM are too heavy).

| Property | Value |
|---|---|
| Engine | llama-server (in-tree `pheno/model_manager.py` speaks it) |
| Default port | 8080 |
| HTTP API | OpenAI-compatible `/v1/chat/completions` |
| Per-model command | `llama-server -m <gguf> --host 127.0.0.1 --port 8080 -c 8192` |
| Cold start (24 GB) | ~3 s for 0.8 B Q4_K_M |
| Continuous batching | on |
| Chunked prefill | on (via `-cmoe` for MoE) |
| Prefix cache | on (via `--cache-type-k q8_0` etc.) |
| Spec-dec on llama.cpp | draft-model (EAGLE), n-gram, MTP (via `protoLabsAI/Ornith-1.0-9B-MTP-GGUF`) |
| Custom CUDA kernels | depends on build (cuBLAS only on default; custom kernels for K/V offload, etc.) |
| Disk | ~150 MB (prebuilt), ~3 GB (from source + custom CUDA) |
| Build time | 0 (prebuilt) to 90 min (from source) |

### Install commands

```powershell
# Prebuilt (fastest bootstrap)
winget install llama.cpp

# Or scoop
scoop install llama.cpp

# Launch with Qwen3.5-0.8B Q4_K_M GGUF
huggingface-cli download Qwen/Qwen3.5-0.8B-GGUF qwen3.5-0.8b-instruct-q4_k_m.gguf --local-dir D:\koosh\pheno-harness\state\model_cache\qwen35-08b
llama-server -m D:\koosh\pheno-harness\state\model_cache\qwen35-08b\qwen3.5-0.8b-instruct-q4_k_m.gguf --host 127.0.0.1 --port 8080 -c 8192
```

## Tier 4: TensorRT-LLM (measured third, not default)

**Use for:** steady-state latency after model is locked + recompile is
acceptable. Only `local/lfm25-8b-a1b-trtllm` lists it, and only as
`planned_compile_once`. Useful for the production hot path once we know
which model wins; not useful for the eval sweep.

| Property | Value |
|---|---|
| Engine | Current stable comparison pin: TensorRT-LLM 1.2.1; the isolated DFlash path uses 1.3.0rc20 only where explicitly admitted |
| Default port | 8002 |
| HTTP API | OpenAI-compatible via `trtllm-serve` |
| Cold start (24 GB, after compile) | Remeasure per compiled engine/artifact |
| Compile per model | Measure on the Ampere 3090 Ti; do not reuse Ada estimates |
| Spec-dec on TRT-LLM | draft-model (EAGLE), n-gram, MTP via plugin |
| Custom CUDA kernels | full (TensorRT engine is the kernel) |
| Disk | ~3 GB (engine + triton) |
| Build time | Measure locally; no inherited Ada/Blackwell estimate |

### Install commands (only if we go down this path)

```powershell
# Gated example only; do not install until a tournament winner is authorized.
pip install tensorrt-llm==1.2.1 --extra-index-url https://pypi.nvidia.com

# Compile a checkpoint
trtllm-build --model_dir <hf_repo_or_engine> --output_dir <engine_dir> --max_batch_size 32 --max_input_len 8192

# Serve
trtllm-serve <engine_dir> --host 127.0.0.1 --port 8002
```

## What to do after engine install (post-round-6 path)

1. **Pick the per-model engine** from the matrix above. Default: SGLang
   for L2/L3 (LFMs, Ornith), vLLM for the spec-dec sweeps, llama.cpp
   only for L1 (Qwen3.5-0.8B) when SGLang/vLLM are too heavy.
2. **Download weights** for the target model (only when ready to launch).
3. **Launch the engine** with the per-tier command above.
4. **Re-run `probe_pheno_serve.py --json`** — the `tcp.ok` field should
   flip from `false` to `true` for the chosen profile.
5. **Run `smoke_pheno_serve.py` without `--skip-completion`** to verify
   `/v1/chat/completions` works end-to-end.
6. **Run the perf probe** (`scripts/bench_pheno_serve.py --profile
   local/qwen35-08b --batch 1 --batch 4 --iters 16 --output
   bench/results/2026-07-04/perf_qwen35-08b.json`).
7. **Run the spec-dec trial** if the engine supports it (SGLang /
   vLLM / llama.cpp all do; SGLang via `--speculative-draft-model-path`,
   vLLM via `--speculative-model`, llama.cpp via `--model-draft`).
8. **Update the round-7 close-out** with actual numbers, then close
   items 3, 4, 6, 7 from the round-6 todo list.

## Recommended first probe (revised round-7 plan)

SGLang on `Qwen/Qwen3.5-0.8B` — the smallest, fastest, drafter-tier model:

- Cold start ~10 s.
- TTFT target: historical hypothesis only; remeasure Qwen3.5 + SGLang on the Ampere 3090 Ti.
- ITL p50 target: <12 ms.
- Decode target: >250 tok/s.
- Acceptance rate with self-draft (EAGLE-2): >0.45.
- vRAM: <3 GB BF16.
- Disk: ~5 GB SGLang + 1.7 GB weights.
- Cost: $0 cloud, ~5 min wall.

Then add the spec-dec layer (EAGLE-2 with a 0.5 B Qwen draft) and re-measure.

## Cross-references

- `config/inference_runners.yaml` — repo's canonical runner list (sglang primary, vllm secondary, llama_server fallback)
- `config/decode_acceleration_matrix.yaml` — first decode sweep is EAGLE-3 on vLLM
- `config/local_model_bench_matrix.yaml` — locked engines per model
- `config/pheno_serve.yaml` — proxy + per-profile engine assignments
- `docs/ARCHITECTURE_LAYERS.md` — `pheno-serve-dev` is the canonical local engine-lifecycle layer
- `docs/adrs/0006-pheno-serve-dev-bootstrap.md` — round-6 bootstrap ADR
- `docs/specs/003-model-engine-matrix.md` — tier × engine matrix + spec-dec zoo
