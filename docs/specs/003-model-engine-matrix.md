# 003 — Model × Engine Matrix

> **Status:** Design. Pairs with `config/model_engine_matrix.yaml` (new) and the perf suite under `perf/*`.
> **Naming convention:** forks we own carry the `-dev` suffix in bin/path names (`forge-dev`, `omniroute-dev`, `pheno-serve-dev`, `codex-dev`). The matrix references engines by their upstream names (vLLM, SGLang, TensorRT-LLM, llama.cpp / MLX) but binds them through `omniroute-dev` (cloud routing) and `pheno-serve-dev` (local engine lifecycle + OpenAI-compat endpoint).
> **Source of truth for model SKUs:** the active local-only lock in `config/local_model_bench_matrix.yaml`. The broader HF shortlist is research history and must not expand the active evaluation set without a new explicit lock.
> **Updated 2026-07-04:** this document no longer names model SKUs in its tier tables. Picks deferred to the locked shortlist (ADR 0005). Previous round-2 picks (Qwen3-8B AWQ, Qwen3-1.7B GGUF, Qwen2.5-Coder-32B-AWQ) are retained as historical artifacts in `state/hf_scrape/2026-07-03/shortlist.csv` but are superseded by the locked shortlist. See `docs/adrs/0004-stale-sku-retrospective.md` for why.

---

## 0. Constraints recap

- **Primary hardware:** Windows desktop, 64 GB DDR4, RTX 3090 Ti (24 GB VRAM, GA102, **no FP8 tensor cores**).
- **Secondary hardware:** M1 Pro MacBook Pro, 10-core, 16 GB RAM. Worker / fallback only.
- **Cloud baselines:** historical/research-only. Cloud execution and routing are disabled by the active local-only evaluation policy; no cloud model is scoreable in the current run.
- **Active local evaluation set:** `local/qwen35-08b`, `local/lfm25-8b-a1b`, and `local/ornith-8b`, with only explicitly hash-locked local artifacts.
- **Density rule:** ≤ 12 B dense local is fine. > 12 B → MoE preferred (or quantized).
- **Engine rule:** vLLM, SGLang, TensorRT-LLM, llama.cpp / MLX (M1 fallback) are all in scope.
- **Optimization rule:** prefix-cache, chunked prefill, in-flight batching, speculative decoding (EAGLE / P-EAGLE / N-gram / Suffix / MLP-draft), quantization (AWQ / GPTQ / GGUF / FP8 / INT8), CUDA-graph capture, custom kernels — all permitted.

Pheno-harness already encodes `SGLang primary, vLLM secondary, llama-server legacy, BitNet sub-1B` in `config/inference_runners.yaml`. TensorRT-LLM is `not_recommended_primary` because of compile overhead on 3090 Ti. We honor that on 3090 Ti and re-evaluate on Blackwell.

---

## 1. Tier system (size bands only; SKUs in locked_shortlist.md)

| Tier | Size band | Default engine (3090 Ti) | M1 Pro fallback |
|---|---|---|---|
| `T0_draft` | ≤ 2 B dense | ik_llama / llama.cpp | llama.cpp / MLX |
| `T1_small` | 2–4 B dense | SGLang | llama.cpp |
| `T2_mid` | 4–12 B dense | SGLang (AWQ) or vLLM (AWQ) | (skip — too large) |
| `T3_mid_moe` | 12–48 B MoE (active ≤ 4 B) | vLLM (AWQ) or SGLang | (skip) |
| `T4_ceiling_dense` | 24–35 B dense (AWQ-INT4 only) | vLLM (AWQ) | (skip) |
| `T5_cloud` | any, cloud | OpenRouter via `omniroute-dev` | same |

Tier keys are referenced by `harness/lanes.yaml`, `config/models.yaml`, and `config/local_swarm.yaml`. The matrix itself lives in `config/model_engine_matrix.yaml` (new).

**Naming change from round-2:** tier names are now size-band-only (`T3_mid_moe`, `T4_ceiling_dense`) instead of size-band + engine-hint (`T3_moe_mid`, `T4_moe_large`). The round-2 naming implied that T3 was always MoE and T4 was always MoE; reality is that T4 is dense-on-AWQ-INT4, T3 is MoE-with-low-active-ratio. Fixing the naming now prevents future confusion.

---

## 2. Model list

### 2.0 Active local lock

The current evaluation set is intentionally small and fixed while the harness and hardware placement are being optimized:

| Alias | Source family | Active artifact policy |
|---|---|---|
| `local/qwen35-08b` | `Qwen/Qwen3.5-0.8B` | GGUF Q2-Q8 bakeoff; Q4 baseline hash-locked |
| `local/lfm25-8b-a1b` | `LiquidAI/LFM2.5-8B-A1B` | GGUF Q4 baseline hash-locked |
| `local/ornith-8b` | `deepreinforce-ai/Ornith-1.0-9B` | Published grafted MTP Q4 GGUF; direct base conversion is not substituted |

No other model SKU is active in the local score matrix. The active artifacts remain subject to runtime, semantic-quality, and reproducibility gates.

### 2.0.1 Historical shortlist

The broader shortlist below is retained for research history and future review only. It is not an execution authorization.

The current picks are in `state/hf_scrape/2026-07-04/locked_shortlist.md` — locked per ADR 0005 with recency stamps + OR + HF pricing. This section stays here as the **historical record** of round-2 picks, marked as superseded.

### 2.1 (superseded) Tier 0 — drafts (≤ 2 B), round-2 picks

Live 2026-07-03 shortlist (kept for diff against v2 shortlist):

| Model | Size | Format | Downloads (2026-07-03) | Notes |
|---|---|---|---:|---|
| `Qwen/Qwen3-1.7B` | 2.03 B | GGUF Q4_0 | 1.8 M | round-2 drafter pick |
| `Qwen/Qwen2.5-0.5B-Instruct` | 0.49 B | GGUF Q4_K_M | 4.0 M | alt drafter, near-1B floor |
| `meta-llama/Llama-3.2-1B-Instruct` | 1.24 B | GGUF Q4_0 | 8.9 M | cross-check drafter |
| `google/gemma-3-1b-it` | 1.0 B | GGUF Q4_0 | 4.0 M | safety-comparison drafter |

**v2 shortlist supersedes this:** the v2 shortlist's T0 drafter pick is `google/gemma-4-E2B-it-qat-q4_0-gguf` (Gemma-4 family, June 2026 release, 348 K downloads in 1 month). `Qwen3-1.7B` and the others remain as candidates but were not selected.

### 2.2 (superseded) Tier 1 — small (2–4 B), round-2 picks

| Model | Size | Format | Downloads (2026-07-03) | Notes |
|---|---|---|---:|---|
| `Qwen/Qwen3-4B-Instruct-2507` | 4.02 B | AWQ-INT4 | 5.3 M | round-2 T1 pick (July 2025 refresh) |
| `meta-llama/Llama-3.2-3B-Instruct` | 3.21 B | AWQ | 2.2 M | cross-check |
| `microsoft/Phi-3.5-mini-instruct` | 3.82 B | AWQ | 22 M | strong baseline at this size |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` | 1.54 B | AWQ | 12 M | sub-2B code baseline |

**v2 shortlist supersedes this:** the v2 shortlist's T1 default pick is `google/gemma-4-12B-it-qat-q4_0-gguf` (Gemma-4 12 B, June 2026 release, 559 K GGUF Q4_0 downloads).

### 2.3 (superseded) Tier 2 — mid (4–12 B dense), round-2 picks

| Model | Size | Format | Downloads (2026-07-03) | Notes |
|---|---|---|---:|---|
| `Qwen/Qwen3-8B` | 8.19 B | AWQ-INT4 | 15.3 M | round-2 T2 workhorse |
| `meta-llama/Llama-3.1-8B-Instruct` | 8.03 B | AWQ | 9.5 M | baseline + regression reference |
| `Qwen/Qwen2.5-Coder-7B-Instruct` | 7.62 B | AWQ | (per model card) | code-specialized T2 |

**v2 shortlist supersedes this:** the v2 shortlist's T2 workhorse pick is `Qwen/Qwen3-Coder-Next-FP8` (Feb 2026 release, 2.17 M downloads, coding-specialized, 262 K context). Alternative T2 candidates: `ibm-granite/granite-4.1-8b`, `LiquidAI/LFM2.5-8B-A1B`. Open question — see v2 shortlist.

### 2.4 (superseded) Tier 3 — MoE mid (12–48 B), round-2 picks

| Model | Total | Active | Format | Downloads (2026-07-03) | Notes |
|---|---:|---|---|---:|---|
| `Qwen/Qwen3-Coder-30B-A3B-Instruct-AWQ` | 30.5 B | 3.0 B | AWQ-INT4 | (model card) | round-2 T3 pick (MoE mid coding) |
| `Qwen/Qwen3-30B-A3B-Instruct-2507` | 30.5 B | 3.0 B | AWQ-INT4 | 993 K | T3 alt (general) |
| `allenai/OLMoE-1B-7B-0125` | 6.9 B | 1.0 B | BF16 (fits) | (per model card) | open-weights MoE mid |

**v2 shortlist supersedes this:** the v2 shortlist's T3 MoE mid pick is `moonshotai/Kimi-Linear-48B-A3B-Instruct` (48 B total / 3 B active, linear attention, 70 K downloads). Note: linear attention may not be natively supported by SGLang/vLLM at the time of eval; needs verification before slotting.

### 2.5 (superseded) Tier 4 — ceiling dense (24–35 B), round-2 picks

| Model | Total | Format | Notes |
|---:|---|---|---|
| `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` | 32.76 B | AWQ-INT4 | round-2 T4 workhorse |
| `meta-llama/Llama-3.1-70B-Instruct-AWQ` (gated) | 70 B | AWQ + CPU offload | dense-large reference |
| `Qwen/Qwen3-32B` | 32.76 B | AWQ-INT4 | general T4 alt |
| `01-ai/Yi-1.5-34B-Chat` (gated) | 34.4 B | AWQ-INT4 | dense large alt |
| `meta-llama/CodeLlama-34b-Instruct-hf` | 33.7 B | AWQ-INT4 | code-specialized T4 |

**v2 shortlist supersedes this:** the v2 shortlist's T4 ceiling dense pick is `mistralai/Devstral-Small-2-24B-Instruct-2512` (24 B dense coding-specialized, released 2026-06-30, 348 K downloads, requires AWQ-INT4 to fit on 3090 Ti). Alternative: `Qwen/Qwen3.5-27B` (April 2026, 2.5 M downloads, 27 B dense, requires AWQ-INT4).

### 2.6 Historical cloud baselines (not executable)

| Model | Provider | Notes |
|---|---|---|
| `inclusionai/ling-2.6-flash` | OpenRouter | primary cloud baseline |
| `ibm-granite/granite-4.0-h-micro` | OpenRouter | cheap micro baseline |
| `liquid/lfm-2-24b-a2b` | OpenRouter | alt-architecture MoE baseline |
| `arcee-ai/trinity-mini` | OpenRouter | small cloud baseline |
| `ibm-granite/granite-4.1-8b` | OpenRouter | enterprise 8B baseline |
| `poolside/laguna-xs-2.1` | OpenRouter | coding cloud baseline |
| `tencent/hy3-preview` | OpenRouter | preview cloud baseline |
| `qwen/qwen3.5-flash-02-23` | OpenRouter | Qwen flash cloud baseline |

---

## 3. Engine × tier matrix (3090 Ti primary)

`✓` = primary path; `◐` = secondary; `✗` = not supported / not recommended.

| Engine | T0 | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|
| ik_llama / llama.cpp | ✓ | ✓ | ◐ | ✗ | ✗ |
| SGLang | ✓ | ✓ | ✓ | ✓ | ◐ |
| vLLM | ✓ | ✓ | ✓ | ✓ | ✓ |
| TensorRT-LLM | ◐ | ◐ | ◐ | ◐ | ◐ |
| BitNet | ✓ (≤ 1B ternary) | ✗ | ✗ | ✗ | ✗ |
| MLX (M1 Pro fallback only) | ✓ | ◐ | ✗ | ✗ | ✗ |

**Why this is the recommendation:**
- **T0 (drafts):** ik_llama / llama.cpp are lowest-overhead and pair naturally with speculative decoding (spec-dec needs a tiny draft model; this tier is the draft).
- **T1 (small):** SGLang's low-latency RadixAttention is excellent for the chat-loop's tight inner loop. vLLM is also fine.
- **T2 (mid):** SGLang and vLLM are roughly tied at this size on 3090 Ti. TensorRT-LLM is `◐` only because compile overhead is painful for nightly iteration; worth running once per release.
- **T3 (MoE mid):** vLLM's paged KV + chunked prefill wins for MoE on consumer GPUs. SGLang viable but slightly behind.
- **T4 (dense ceiling):** vLLM with AWQ-INT4 is the realistic local option. TensorRT-LLM `◐` because compile is rarely worth it for a single nightly.

---

## 4. Quantization strategy per tier

- **T0:** GGUF Q4_K_M. No AWQ (too coarse).
- **T1:** AWQ-INT4 default; GGUF Q5_K_M fallback for M1 Pro.
- **T2:** AWQ-INT4 default. FP8 not available on 3090 Ti (no tensor-core FP8).
- **T3 (MoE):** AWQ-INT4 on active experts; experts offloaded to CPU with `vllm cpu_offload` / SGLang equivalent.
- **T4 (dense ceiling):** AWQ-INT4 + tight KV budget; expect batch size 1 only.
- **M1 Pro:** GGUF Q4_K_M only. No FP8, no AWQ on MLX in stable form as of mid-2026.

---

## 5. Speculative decoding strategy per tier

The spec-dec zoo is wider than just EAGLE/Medusa. Per user 2026-07-04, the frontier includes:

| Spec-dec mode | Family | Engine support | Notes |
|---|---|---|---|
| **EAGLE-2** | self-speculative (vanilla) | SGLang, vLLM, TRT-LLM | baseline; trained-from-base draft head |
| **EAGLE-3** | self-speculative (lookahead) | SGLang, vLLM | lookahead draft features |
| **P-EAGLE** | self-speculative | vLLM | parallel EAGLE draft |
| **Medusa** | head-based parallel candidates | vLLM, llama.cpp | per-position multi-token heads |
| **PLD** | prompt lookup | vLLM, llama.cpp | draft-from-prompt, no draft model |
| **Lookahead decoding** | Jacobi iteration | SGLang, vLLM, TRT-LLM | parallel-tree speculation |
| **N-gram** | suffix-matching draft | vLLM | cheap, low-overhead |
| **Suffix-decoding** | suffix-tree draft | vLLM | cache-friendly |
| **MLP-draft / Speculators** | learned small MLP draft | vLLM | HuggingFace Speculators library |
| **MTP (multi-token prediction)** | trained-in | TRT-LLM, llama.cpp (MTP-GGUF), partial SGLang | live on `protoLabsAI/Ornith-1.0-9B-MTP-GGUF`; not all engines have native MTP yet |
| **DSpark** | diffusion-based spec-dec | (TBD engine; not yet in SGLang/vLLM stable) | per user 2026-07-04: "dflash-like diffusion speculative decoder" |
| **JetSpec** | jet-iteration spec-dec | (TBD) | per user; experimental |
| **DDTree** | diffusion-decision-tree spec-dec | (TBD) | per user; experimental |
| **Speculative-speculative** | multi-branch speculation (more than one draft path per token) | (TBD) | per user 2026-07-04: "intentional double type, speculating all possible options rather than just 1 for a given token" |

Tier bindings (what we actually run per tier):

| Tier | Draft | Spec-dec mode |
|---|---|---|
| T0 | self (T0 model is the draft for T1+) | EAGLE-2 / P-EAGLE |
| T1 | T0 draft | EAGLE-2 / P-EAGLE; N-gram for cache-warm prompts |
| T2 | T0 or T1 draft | EAGLE-2 / dynamic spec-dec |
| T3 (MoE) | T1 draft (CPU) | EAGLE-2 only; N-gram when prefix-cache is hot |
| T4 (dense ceiling) | T1 draft (CPU) | EAGLE-2 only |
| Cloud (Ling) | server-side (provider controls) | unknown; measure and report |

Engine coverage for the spec-dec zoo:

- **SGLang 0.5.2**: EAGLE-2, MTP (partial), Lookahead, N-gram. **Primary** path for `forge-dev`.
- **vLLM 0.20.0**: EAGLE-2/3, Medusa, PLD, N-gram, Suffix, Speculators, Lookahead. **Secondary**.
- **TensorRT-LLM**: EAGLE, MTP, Lookahead. `◐` on 3090 Ti (compile overhead).
- **llama.cpp**: MTP-GGUF (`protoLabsAI/Ornith-1.0-9B-MTP-GGUF` is the canonical MTP test case), PLD, Lookahead.

**DSpark / JetSpec / DDTree / Spec-Spec status as of 2026-07-04:** none have native SGLang or vLLM support in the public release tracks. They are research-frontier modes. Pheno-harness does **not** ship them as eval targets in round 1; they are tracked in the corpus (`D:\koosh\Downloads\ChatGPT-Agent-Aware Speculative Decoding.md`) and revisited when an engine lands native support.

Pheno-harness's `config/decode_acceleration_matrix.yaml` is the existing policy file. New spec-dec bindings go there.

---

## 6. vRAM budget on RTX 3090 Ti (24 GB) — vRAM truth table

This is the **honest fit table**. Specific model names are deferred to `v2_shortlist.md`; this table is the math underlying those picks.

| Class | BF16 weight size | Fits BF16 on 3090 Ti? | AWQ-INT4 size | Fits AWQ? |
|---|---:|:---:|---:|:---:|
| 1–3 B dense | 2–6 GB | YES | 1–2 GB | YES |
| 4–8 B dense | 8–16 GB | borderline | 3–5 GB | YES |
| 12 B dense | 24 GB | exactly (no KV headroom) | 7 GB | YES |
| 24 B dense | 48 GB | **NO** | 13 GB | YES (with KV budget) |
| 27 B dense | 54 GB | **NO** | 15 GB | YES (tight) |
| 32 B dense | 64 GB | **NO** | 18 GB | YES |
| 35 B dense | 70 GB | **NO** | 20 GB | YES (max) |
| 48 B MoE (3 B active) | 96 GB total | **NO**; only 6 GB of weights activated | 27 GB | borderline |
| 122 B MoE (10 B active) | 244 GB total | **NO** | 68 GB | **NO** |

**Principles:**
- BF16 dense weights ≠ usable on 3090 Ti at > 12 B; AWQ-INT4 / 4-bit GGUF only.
- MoE params_total only saves compute, not VRAM — all weights must be resident.
- AWQ-INT4 fit is the gating constraint for any model > 12 B.
- The 3090 Ti ceiling at AWQ-INT4 is ~35 B (≈ 20 GB weights + ~4 GB KV/activations).

**Long-context spill:** at 128K+ context, KV cache dominates. SGLang RadixAttention and vLLM paged KV both handle 128K; 262K (Ling-tier) likely needs chunked prefill + KV offload to CPU RAM.

---

## 7. Parallel agent sweep targets

Local 3090 Ti can sustain one T2 / T3 model at batch 1 reliably. Parallel agent count is bounded by both VRAM and effective concurrency. These are **targets**, not measurements.

| Agents | Tier achievable | Target ttft p95 |
|---|---|---|
| 1 | T4 (24–35 B AWQ-INT4) | < 200 ms |
| 2 | T3 (48 B MoE AWQ, low active ratio) | < 250 ms |
| 4 | T2 (8–12 B AWQ) | < 300 ms |
| 8 | T1 (2–4 B AWQ) | < 400 ms |
| 16 | T0 + spec-dec (2 B GGUF) | < 500 ms |
| 32+ | Cloud only | (use OpenRouter) |

Sweep script is `perf/parallel_sweep.py` and emits `bench/results/perf/<date>_parallel_<n>.json` per cell. The exact SKUs at each tier come from the v2 shortlist's T0–T4 picks.

---

## 8. M1 Pro fallback matrix (16 GB RAM)

M1 Pro is a worker / fallback only. Quantization restricted to GGUF Q4_K_M. Spec-dec on draft only.

| Tier | M1 Pro feasible? |
|---|---|
| T0 (≤ 2 B GGUF Q4_0) | yes |
| T1 (≤ 4 B GGUF Q4_K_M) | yes, slow |
| T2 (4–12 B) | no — RAM-bound, not VRAM |
| T3+ | no |

Use M1 Pro for: cache-warming, draft token generation, monitoring, and emergency fallback when 3090 Ti is busy.

---

## 9. Perf probes (what `perf/*` actually measures)

| Probe | Output | Use |
|---|---|---|
| `perf/ttft_probe.py` | TTFT p50/p95/p99 | per engine × tier × batch |
| `perf/cache_probe.py` | prefix-cache hit rate | canonicalized vs. raw prompts |
| `perf/harness_overhead.py` | harness wall time − model wall time | identify non-model latency |
| `perf/parallel_sweep.py` | N-agent fan-out | sweep N ∈ {1, 2, 4, 8, 16, 32} |
| `perf/profiler.py` | CPU/RAM/VRAM/disk/net + queue depth + leaks + deadlocks | always-on during every eval run |
| `perf/report.py` | roll-up → `bench/results/perf/<date>/` | human-readable summary |

**Crucial rule:** every probe run is paired with a non-probe reference run on the same model + same workload. The diff between probe-attached and probe-detached is the **probe overhead** itself, which is reported separately so we don't double-count.

---

## 10. Historical cost / price reference (July 2026)

Cloud pricing below is retained only for a future re-enable decision. It is not an execution plan, and no cloud route is allowed by the current local-only lock.

**Cloud baselines (8 models, OpenRouter — per ADR 0005):**

| OR id | Prompt $/M | Completion $/M | OR created | recency |
|---|---:|---:|---|---|
| `inclusionai/ling-2.6-flash` | $0.01 | $0.03 | 2026-04-21 | ✓ |
| `ibm-granite/granite-4.0-h-micro` | $0.017 | $0.112 | 2025-10-20 | **PRE-MARCH (DLQ)** |
| `liquid/lfm-2-24b-a2b` | $0.03 | $0.12 | 2026-02-25 / HF 2026-03-30 | ✓ (HF repo fresh) |
| `arcee-ai/trinity-mini` | $0.045 | $0.15 | 2025-12-01 / HF 2026-05-28 | ✓ (HF repo fresh) |
| `ibm-granite/granite-4.1-8b` | $0.05 | $0.10 | 2026-04-30 / HF 2026-05-04 | ✓ |
| `poolside/laguna-xs-2.1` | $0.06 | $0.12 | 2026-07-02 | ✓ |
| `tencent/hy3-preview` | $0.063 | $0.21 | 2026-04-23 | ✓ |
| `qwen/qwen3.5-flash-02-23` | $0.065 | $0.26 | 2026-02-25 / HF TBD | needs re-probe |

**Self-hosted (3 models, per ADR 0005):** Qwen3.5 0.8B (`local/qwen35-08b`), LiquidAI LFM 2.5 8B-A1B (`local/lfm25-8b-a1b`), and the published grafted Ornith MTP Q4 artifact (`local/ornith-8b`). Exact artifact evidence is recorded in `state/*_q4_gguf_manifest.json` and `state/ornith_mtp_q4_manifest.json`. Pricing = amortized electricity only.

**Historical full-sweep estimate** (8 cloud × TB2.0+DeepSWE+SWE-bench Verified × 3 attempts/task):
- ~$30–80 per model
- ~$240–640 for the full cloud baseline (1 sweep)
- Local models: ~$0 (electricity only)

**Current cost cap per eval run:** local-only, $0 model cost. Any future cloud re-enable must first project the combined run at no more than $1 and receive an explicit policy change.

**Cloud pricing watch:** retained as research data only; it must not trigger automatic routing or fallback.

---

## 11. Open decisions

These are the open items **as of 2026-07-04**. Anything resolved is moved to ADR 0005 or below; nothing stays open without a YAML owner + a target date.

**Signed off (per `docs/adrs/0005-locked-baseline-march-2026-cutoff.md`):**

1. **Self-hosted models locked to exactly 3 aliases:** `local/qwen35-08b`, `local/lfm25-8b-a1b`, `local/ornith-8b`. No b16 / BitNet / arbitrary T1 / T2 picks.
2. **Cloud baselines are retained as historical research only:** new evaluation runs are local-only until the user re-enables cloud evaluation and the combined run cost is projected at no more than $1.
3. **Recency cutoff = 2026-03-01.** Models older than that are flagged `PRE-MARCH (DLQ)` and require explicit justification in research notes.
4. **b16 (BitNet b1.58) is not a candidate.** Dropped; was never in corpus.
5. **Spec-dec zoo (DSpark / JetSpec / MTP / DDTree / speculative-speculative) is in scope** per §5.
6. **`HF_TOKEN` handling rule:** env-var-only, never logged, never committed, set/unset via one-shot wrapper per `state/_round4_run.ps1`.

**Pending sign-off / superseded by local-only policy:**

1. `ibm-granite/granite-4.0-h-micro` is PRE-MARCH (2025-10-20 OR / 2025-11-03 HF). Keep (cheapest cloud at $0.017 / $0.112) or drop?
2. `qwen/qwen3.5-flash-02-23` has HF repo 404 — re-probe canonical id or drop?
3. `arcee-ai/Trinity-Mini` has `custom_code` flag — retained only as a future cloud research item.
4. **Engine matrix:** SGLang primary, vLLM cross-check, TensorRT-LLM compile/probe, and llama.cpp / MLX for M1 Pro. Pascal remains llama.cpp CUDA 12.4 only.
5. **Long-horizon local strategy:** first complete the three locked local models and the hardware-aware independent-worker matrix before adding any larger SKU.

**No new SKU additions until these resolve.** Per ADR 0004 rule #4.

---

## 12. First matrix sweep (the actual waypoint)

The sweep order is **fixed**; the SKUs at each tier are the **locked picks from ADR 0005**.

1. **T0 sweep:** `Qwen/Qwen3.5-0.8B` + spec-dec draft candidates × SGLang + vLLM + llama.cpp. Confirm Qwen3.5-0.8B as the universal drafter.
2. **T1/T2 sweep:** `local/lfm25-8b-a1b` + `local/ornith-8b` × SGLang + vLLM + llama.cpp. Pick best per-task-type after exact artifacts are confirmed.
3. **Local engine sweep:** the three locked models × llama.cpp, SGLang, vLLM, and TensorRT-LLM where architecture and GPU capability permit.
4. **Hardware topology sweep:** 3090 primary, 1080 helper, CPU/DDR4/NVMe cold tiers; independent queues before any tensor parallelism.
5. **Spec-dec zoo eval:** DSpark / JetSpec / MTP / DDTree / speculative-speculative where the selected runtime and model expose a verifiable implementation.
6. **M1 Pro fallback:** Qwen3.5-0.8B and LFM2.5-8B-A1B on llama.cpp / MLX; latency profile + sustained throughput.

Run artifacts: `bench/results/perf/<date>_t<n>_<model>_<engine>.json`. Roll-up: `bench/results/perf/<date>_rollup.json`. Reports: `docs/adrs/<NNNN>-<date>-<topic>.md` per material finding.

**No PR merges core harness changes without a benchmark artifact.** Per `RISKS.md` §19.
