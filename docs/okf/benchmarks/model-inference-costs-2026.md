---
source_file: ChatGPT-Model Inference Costs 2026.md
sha256: placeholder-model-inference-costs-2026
topics: [benchmarks, inference, cost, latency]
related_okf:
  - benchmarks/pairwise-test-case-generation.md
  - inference/vram-scaling-factors.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Model Inference Costs 2026

**Source:** `ChatGPT-Model Inference Costs 2026.md` — class **L**.

Benchmark cost/latency tradeoffs for 2026 inference: per-token pricing vs local 3090, batch amortization, KV-cache effects.

## Key insights (stub)

- Cost per 1K tokens varies 10x across providers; local 3090 amortizes after ~10M tokens at $0.35/hr rental.
- Pairwise benchmark reduction (see pairwise-test-case-generation.md) applies to cost/latency evals.
- Eval methodology: measure TTFT, TPOT, and $/verified_pass.

## Next (N10)

- Extract [L] claims with `local://sha256/...` citations.
- Map to `bench/matrix` cost model and `docs/specs/`.
- Promote to [P] after primary source verification.

**Evidence:** `local://sha256/placeholder-model-inference-costs-2026` (class **L**).
