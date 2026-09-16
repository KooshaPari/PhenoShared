---
source_file: ChatGPT-VRAM and Scaling Factors (1).md
sha256: c15bb484032ac8c9cefafd4afbe617f214a9370354183bdd2ab26d0f0ddd6032
topics: [inference, VRAM, KV-cache, MoE, concurrency, HuggingFace]
related_okf:
  - hardware/rtx-3090-throughput.md
  - inference/agent-aware-speculative-decoding.md
evidence_class: L
---

# VRAM and Scaling Factors

Hugging Face model-card VRAM figures are overwhelmingly **weights-fit numbers** for short inputs (~≤1024 tokens), near-single-request conditions, and minimal KV pressure—not production long-context or multi-agent serving budgets. Real capacity planning decomposes memory as **weights + runtime overhead + KV cache**, where KV grows with **total live tokens across all active sequences**; “concurrency” should be modeled as a token budget, not a user count, with dense vs MoE diverging on compute but converging on KV limits.

## Key insights

- **HF default assumption:** ~2 GB per 1B params (bf16/fp16) dominates only when prompts are short; card numbers like “18 GB” on quantized MoE cards are baseline load costs, not “18 GB at 262K context.”
- **Concurrency formula:** `effective concurrency ≈ KV-token-budget / avg live tokens per request`, where live tokens = prompt tokens kept alive + generated tokens still resident.
- **Served concurrency:** `min(compute-limited concurrency, KV-limited concurrency)` — whichever binds first wins.
- **Dense vs MoE split:**
  - **VRAM fit:** size by **total loaded parameters** (full MoE state in memory).
  - **Decode throughput:** scale by **active parameters** per token.
  - **Context/concurrency:** both behave similarly—KV cache scales with attention stack and live tokens; MoE improves tok/s but not long-context memory headroom.
- **Slider UX model:** `displayed_memory = base_model_memory + context_overhead + concurrency_overhead`, driven internally by `token_pressure = concurrent_sequences × avg_live_tokens_per_sequence`.
- **Example (Qwen3.6-35B-A3B @ 18 GB):** fit as 35B-class footprint; throughput as ~3B-active MoE; context slider still adds KV linearly with live tokens.
- **vLLM knobs:** `gpu_memory_utilization`, `kv_cache_memory_bytes`, `max_num_seqs`, and `max_num_batched_tokens` explicitly trade concurrency vs memory.

## Pheno-harness links

- [`docs/specs/003-model-engine-matrix.md`](../../specs/003-model-engine-matrix.md) — tier bands (T3 MoE, T4 dense AWQ) and 3090 Ti 24 GB constraint.
- [`config/inference_runners.yaml`](../../config/inference_runners.yaml) — engine memory utilization and batching defaults.
- [`plans/2026-07-14-usch-heterogeneous-inference-v1/FLEET_READINESS.md`](../../plans/2026-07-14-usch-heterogeneous-inference-v1/FLEET_READINESS.md) — heterogeneous device VRAM/KV placement.
- [`plans/2026-07-14-usch-heterogeneous-inference-v1/EXPERIMENT_AND_DISCOVERY_PLAN.md`](../../plans/2026-07-14-usch-heterogeneous-inference-v1/EXPERIMENT_AND_DISCOVERY_PLAN.md) — concurrency and cache experiments.

**Evidence:** `local://sha256/c15bb484032ac8c9cefafd4afbe617f214a9370354183bdd2ab26d0f0ddd6032` (class **L**; cross-check HF optimization docs and vLLM engine args before **P**).
