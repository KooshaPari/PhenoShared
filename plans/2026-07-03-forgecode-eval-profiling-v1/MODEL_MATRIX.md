# MODEL_MATRIX.md

Date: 2026-07-03
Companion to: `EVAL_ARCHITECTURE.md`, `RESEARCH_AUDIT.md`,
`TRACE_EVALSET_PLAN.md`, `IMPLEMENTATION_PLAN.md`, `RISKS.md`.

Defines the **tiers**, **candidates**, and **inference engines** to
exhaustively sweep on the Windows primary (3090 Ti 24 GB) and the M1 Pro
secondary. Constraint reminders:

- 24 GB VRAM (3090 Ti) is the binding desktop ceiling.
- 64 GB DDR4, **2 TB NVMe at ~95% full.**
- Above 12B dense, prefer MoE or heavily quantized.
- For sub-12B, dense is fine; MoE still preferred when available.

This matrix extends (does *not* replace) `config/local_model_bench_matrix.yaml`,
`config/models.yaml`, and `config/inference_runners.yaml`.

---

## 1. Tiers

| Tier | Param range | VRAM budget (Q4_K_M) | Notes |
|---|---|---|---|
| **T0 (draft)** | 0.4B–0.8B | 0.5–0.8 GB | speculative-decoding draft; always resident. |
| **T1 (small)** | 1B–4B | 2–6 GB | coding subagent, fast lanes, M1 Pro. |
| **T2 (mid)** | 7B–12B | 6–10 GB | solo engineer on common issues; 3090 Ti headroom for 12B dense + 0.6B draft. |
| **T3 (MoE-large)** | 20B–35B (active ≤ 7B) | 10–16 GB with FP8/AWQ | "frontier" tier on the desk; ling-tier. |
| **T4 (cloud)** | API only | n/a | OpenRouter default; Ling-2.6-flash baseline. |

> The 24 GB VRAM is functionally: tier up to T2 always resident, T3
> resident only when T2 is swapped (and T0 stays resident as the draft).

---

## 2. Candidate list (open weights + API baseline)

### 2.1 Tier 0 — draft (0.4B–0.8B)

| Model | Why |
|---|---|
| `Qwen/Qwen2.5-0.5B-Instruct` | trivial draft, fast spec-dec. |
| `Qwen/Qwen3-0.6B` | already wired as `0.6B draft` in `pheno/model_manager.py`; **anchor, keep.** |
| `microsoft/bitnet-b1.58-2B-4T` | ternary; BitNet runner wired; sub-1B-effective on perf. |

### 2.2 Tier 1 — small (1B–4B)

| Model | Why | Candidate for |
|---|---|---|
| `Qwen/Qwen3-4B-Instruct-2507-Q4_K_M` | **anchor**, always-on per `pheno/model_manager.py`. | coding subagent, routine lane. |
| `Qwen/Qwen3-1.7B-Instruct-Q4_K_M` | cheap M1 Pro tier. | M1 Pro fallback. |
| `google/gemma-3-4b-it-Q4_K_M` | alt family for diversity. | ablation lane. |
| `mistralai/Mistral-7B-Instruct-v0.3-Q4_K_M` | cross-family anchoring. | ablation lane. |
| `meta-llama/Meta-Llama-3.1-8B-Instruct-Q4_K_M` | baseline for dense 8B. | T1.5 (boundary). |

### 2.3 Tier 2 — mid (7B–12B)

| Model | Why |
|---|---|
| `Qwen/Qwen3-12B-Instruct-Q4_K_M` | **best 12B dense target**, fits 3090 Ti. |
| `mistralai/Mistral-Small-3.1-24B-Instruct-Q4_K_M` | dense 24B borderline; quantize to fit. |
| `microsoft/Phi-4-14B-Reasoning-Q4_K_M` | reasoning-heavy; check 3090 fit. |
| `meta-llama/Meta-Llama-3.3-70B-Instruct-Q3_K_M` | **only** for off-test cloud-bench comparison. |
| `Qwen/Qwen3-Coder-30B-A3B-Instruct` | MoE 30B / 3B-active — strong coding; small active fraction survives 3090. |

### 2.4 Tier 3 — MoE large (20B–35B)

| Model | Active params | Resident cost (FP8) |
|---|---|---|
| `inclusionai/Ling-2.6-Flash` | 7.4B (104B total) | ~9–10 GB FP8 weights, fits 3090 with headroom for KV. **Anchor; matches OpenRouter behavior.** |
| `Qwen/Qwen3-30B-A3B-Instruct-2507` | 3B (30B total) | ~5–6 GB FP8 weights; "deep dense-equivalent" on the desk. |
| `Qwen/Qwen3-235B-A22B-Instruct-2507` | 22B (235B total) | partial offload only; **mostly cloud**. |
| `mistralai/Mistral-Large-2-123B-A12B-Q4_K_M` | 12B (123B total) | ~22 GB Q4 borderline; quantize harder. |
| `inclusionai/Ling-mini-2.6` | 1B (16B total) | ultra-cheap MoE. |

### 2.5 Tier 4 — cloud (API only)

| Model | Endpoint | Cost (verified 2026-07) | Why |
|---|---|---|---|
| `inclusionai/ling-2.6-flash` | OpenRouter | $0.01 / 1M in, $0.03 / 1M out (90% off promo) | brief's anchor; 262 K context. |
| `anthropic/claude-opus-4-7` | OpenRouter | (verify before run) | `architecture` lane today. |
| `openai/gpt-5.5` | OpenRouter | (verify before run) | TB2 leaderboard top. |
| `google/gemini-3.1-pro` | OpenRouter or direct | (verify) | second opinion. |

---

## 3. Inference engines (mandatory coverage)

The brief lists vLLM, SGLang, TensorRT-LLM, llama.cpp/MLX. Pheno has
only llama-server today. Engines are introduced **one at a time** with
the same test matrix so we can compare apples to apples:

| Engine | Status today | Use case | Caveat |
|---|---|---|---|
| **ik_llama-server** | wired (`pheno/model_manager.py`) | primary on Windows; predictable, fast for Qwen + BitNet. | spec-dec handwired. |
| **llama.cpp** | implicit via ik | M1 Pro fallback, mobile. | slow on big MoE. |
| **MLX** | not installed | M1 Pro primary. | verify install on M1 first. |
| **vLLM** | not wired | long horizon + spec-dec + prefix-cache. | already exposes profiling API. |
| **SGLang** | not wired (declared primary in `inference_runners.yaml`) | agentic workflow, fast tool-call parse. | first priority to land. |
| **TensorRT-LLM** | declared `not_recommended_primary` due to compile overhead | batched inference when a model is "stable". | gates by `decode_acceleration_matrix.yaml`. |
| **BitNet / custom kernels** | wired via `scripts/decode_prepare.py` + BitNet runner | draft / quantized dense. | CUDA SM 8.6 on 3090 Ti. |

**Engine introduction order:**

1. **MLX** on M1 Pro — cheapest and isolates a target. PR-5a.
2. **SGLang** on Windows — declared primary already. PR-5b.
3. **vLLM** on Windows — for prefix-cache & NVFP4 (if Blackwell, no; skip on 3090 Ti SM 8.6). PR-5c.
4. **TensorRT-LLM** only when a model is **stable and hot** (Qwen4B for 30 d+), since compile cost gates this. PR-5d.
5. **Custom CUDA kernels** only as needed for spec-dec drafts where
   ik_llama / EAGLE3 cannot match parity. PR-5e.

---

## 4. Quantization + serving optims (per tier)

| Opt | T0 | T1 | T2 | T3 (MoE) | T4 cloud |
|---|---|---|---|---|---|
| Q4_K_M (llama.cpp) | yes | yes | yes | n/a | n/a |
| AWQ | n/a | yes | yes | partial | n/a |
| GPTQ | n/a | yes | yes | partial | n/a |
| FP8 | n/a | depends on kernel | yes | **yes (anchor)** | n/a |
| NVFP4 | n/a | n/a (Blackwell only) | n/a | n/a | n/a |
| Activation sparsity | n/a | experimental | yes (per `activation_edit_policy.yaml`) | yes | n/a |
| BitsAndBytes | n/a | yes | yes | partial | n/a |

| Serving opt | Tier |
|---|---|
| Prefix/KV reuse (vLLM `prefix caching`, SGLang `radix cache`, ik_llama, TRT-LLM) | T2 + T3 |
| Chunked prefill | T2 + T3 |
| Continuous/in-flight batching | T2 + T3 |
| Spec-dec (EAGLE, P-EAGLE, draft pairing) | T2 + T3 with T0 draft resident |
| `agent-aware speculative decoding` selection | T2 + T3 + T4 (selectable) |
| `user_level_deterministic_cache` (KV + canonical prompt) | all tiers, on every repeat |
| CUDA graphs | T2 |

`config/decode_acceleration_matrix.yaml` already declares most of this;
we extend it, not replace it.

---

## 5. 3090 Ti fitting strategy

The 24 GB VRAM ceiling shapes **what can be resident**.

```
T0 (0.6B draft, Q4_K_M, + KV, + speculative logits)
   ~ 0.8 GB resident
T1 (Qwen4B always-on, Q4_K_M, KV cache 8 K)
   ~ 4.5 GB resident
T2 (Qwen12B on demand, Q4_K_M, KV cache 8 K)
   ~ 10 GB resident (only when T1 swapped out)
T3 (Ling-2.6-flash FP8, KV cache 32 K)
   ~ 13–15 GB resident (T1 + T0 swapped out); FP8 chosen because
   Ling is already FP8-friendly (released weight) and the desk budget
   is binding.
```

**Hard rules:**

- The 0.6B draft is **never** swapped out; it is the warm spec-dec base.
- The "always-on" model (T1) is the only one whose presence is unconditional.
- T2/T3 swap policy lives in `config/moe_deploy_policy.yaml` already; the
  plan just adds the **audit hook** (every swap logs to ledger with the
  trace id, model id, target, gain).

---

## 6. M1 Pro secondary

10-core M1 Pro with 16 GB unified memory. Intended as:

- Tier-1 smallest model (`Qwen3-1.7B-Instruct-Q4_K_M` via MLX) as a
  warm-secondary that picks up UI/quick tasks.
- Not a throughput target. Not a serialization target. "Is the model
  alive on the laptop?" is the only signal.
- MLX on M1 Pro and llama.cpp on M1 Pro; verify install before PR-5a
  merges (see `RESEARCH_AUDIT.md` §7).

---

## 7. Ling-2.6-flash baseline (the brief's anchor)

Per `openrouter.ai/inclusionai/ling-2.6-flash`, verified 2026-07-03:

- 104B total params, 7.4B active, agent-oriented MoE.
- 262 K context window.
- $0.01 / 1M in, $0.03 / 1M out (90% off promo).
- Released 2026-04-21.
- Standard OpenAI-compatible API.

Run rules:

- Pin prompt-template version (we don't know it yet; codify it).
- Pin `seed` where supported.
- Set retry policy: jittered exponential backoff, max 5 retries, then
  `verifier_reward = -1` and write to ledger with `provider_failed=true`.

---

## 8. What "covers" the matrix

The matrix is **exhaustively** swept in the following sense:

- For every (tier × engine × serving-opt × quant) cell where a model can
  plausibly run, there is **one row** in `bench/results/model_matrix/*.jsonl`
  emitting `pass@1` on TB2.1 (5-min micro) plus the metrics in
  `EVAL_ARCHITECTURE.md` §3.3.
- For cells where a model **cannot** fit (e.g. 70B Q4 on 3090 Ti), the
  row is emitted with `runner=failed_to_load` and the reason. This is
  loud failure, not silent omission.

---

## 9. Acceptance criteria for PR-5 (engine adapters)

| Acceptance | How verified |
|---|---|
| MLX serves Qwen3-1.7B on M1 Pro. | `python -m bench.smoke --engine mlx --model …`. |
| SGLang serves Qwen4B + 0.6B draft on 3090 Ti. | `bench/kv_bakeoff.py` replica. |
| vLLM serves Qwen4B with prefix-cache on. | `bench/ctx_cache_probe.py` shows > 50% hit rate on prefix-shared repeats. |
| TRT-LLM compiles Qwen4B (smoke only). | `bench/trt_smoke.py`. |
| Every cell emits the envelope in `EVAL_ARCHITECTURE.md` §2. | per-cell JSON check. |
