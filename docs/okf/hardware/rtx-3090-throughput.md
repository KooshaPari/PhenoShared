---
source_file: ChatGPT-RTX 3090 Throughput Analysis.md
sha256: f76584429acd5d03f42274da14ead8bbb5c2f95b813b3b2ee47f7d3dbbf0e7b1
topics: [hardware, kernels, throughput, RTX-3090, multi-GPU, tok-per-hour]
related_okf:
  - inference/vram-scaling-factors.md
  - inference/agent-aware-speculative-decoding.md
evidence_class: L
---

# RTX 3090 Throughput

For agent-fleet planning on a single RTX 3090/3090 Ti (24 GB GDDR6X, ~1 TB/s bandwidth), the useful metric is **generated output tokens/hour** with separate tracking for prefill/input tokens and KV residency—not single-stream chat tok/s demos. The corpus budgets **150k–350k useful generated tok/hour** for 14B–32B-class coding/agent models (conservative **250k** default), up to **500k–900k** on smaller batched models, with multi-GPU scaling near-linear only under **independent replica** queues (4×3090 ≈ **3.6×**), while tensor-parallel splits yield **~2.3–3.1×** at best; Hopper (H100) jumps **3–7×** mainly via HBM bandwidth, FP8, and concurrency, but many independent agents on cheap 3090s can beat one fancy GPU.

## Key insights

- **Planning constants (conservative):** `3090_agent_safe_output_tph = 250,000`; aggressive = 500,000; small SLM lane ≈ 1.5M; prefill input tph 2M–8M depending on context.
- **Model-class table (1×3090):** 7B–8B Q4 ~70–140 tok/s single (~0.25–0.50M/h); 14B ~45–90 tok/s; 27B–35B MoE/dense Q4 ~20–60 tok/s (~72k–216k/h); 70B offload usually impractical for agent fleets.
- **Replica scaling:** 2× ≈ 1.85–1.95×; 4× ≈ 3.5–3.8×; 8× ≈ 6.5–7.3× — shard agents across GPUs, don’t tensor-parallel unless model/context requires it.
- **Tensor-parallel scaling:** 2×3090 PCIe ~1.35–1.70×; NVLink ~1.50–1.90×; interconnect tax dominates at 4×.
- **Upgrade coefficients vs 3090:** RTX 4090 ~1.25–1.60× (same 24 GB); RTX 6000 Ada ~1.1–1.6× but 48 GB; H100 ~3–7× for strong-model serving endpoints.
- **Stack multiplier:** llama.cpp/ExLlamaV2 for single-node quant experiments; **vLLM/SGLang** for multi-agent API, prefix caching, continuous batching; separate small SLM instances for router/summarizer when possible.
- **Cost gate:** value 1×3090 at **~0.25M useful generated tok/hour** for subscription-replacement math—not cherry-picked benchmark peaks.

## Pheno-harness links

- [`docs/specs/003-model-engine-matrix.md`](../../specs/003-model-engine-matrix.md) — primary hardware: RTX 3090 Ti 24 GB; SGLang primary, vLLM control.
- [`config/inference_runners.yaml`](../../config/inference_runners.yaml) — local runner defaults and speculative configs.
- [`bench/custom/README.md`](../../bench/custom/README.md) — `dual-gpu-perf` and `kernelbench_rtx3090` on 3090 Ti primary lane.
- [`config/benchmark_registry_2026-07.yaml`](../../config/benchmark_registry_2026-07.yaml) — `kernelbench_rtx3090` registry entry.
- [`plans/2026-07-14-usch-heterogeneous-inference-v1/FLEET_READINESS.md`](../../plans/2026-07-14-usch-heterogeneous-inference-v1/FLEET_READINESS.md) — 3090 Ti + optional 1080 Ti fleet posture.

**Evidence:** `local://sha256/f76584429acd5d03f42274da14ead8bbb5c2f95b813b3b2ee47f7d3dbbf0e7b1` (class **L**; validate against live vLLM/SGLang benchmarks before **P**).
