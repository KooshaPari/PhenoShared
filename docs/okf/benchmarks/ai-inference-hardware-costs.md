---
source_file: ChatGPT-AI Inference Hardware Costs.md
sha256: 0ec53079f29772b20135190d51dba1af9ba8b7c8903ea594bb1b90e440729f8e
topics: [benchmarks, hardware, inference, cost]
related_okf:
  - benchmarks/machine-comparison-for-ai.md
  - hardware/rtx-3090-throughput.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# AI Inference Hardware Costs

**Source:** `ChatGPT-AI Inference Hardware Costs (1).md` (8.6 KB, 2026-07-04) — sha `0ec53079` — class **L**.

Hardware cost benchmarks: per-token $ vs local GPU amortization, rental safety, and benchmark design for heterogeneous inference.

## Key insights (stub)

- Inference cost varies 10x across providers; local 3090 amortizes after ~10M tokens at rental rates (see machine-comparison-for-ai.md).
- Hardware cost eval should isolate compute vs memory vs network — link to `bench/matrix` cost model.
- Pairwise benchmark reduction applies to hardware×model combos (see benchmarks/pairwise-test-case-generation.md).

## Next (N10)

- Extract [L] claims with `local://sha256/0ec53079f29772...` citations.
- Map to `bench/contracts/` cost metrics and `config/evidence_registry.yaml`.
- Promote to [P] after primary pricing verification.

**Evidence:** `local://sha256/0ec53079f29772b20135190d51dba1af9ba8b7c8903ea594bb1b90e440729f8e` (class **L**).
