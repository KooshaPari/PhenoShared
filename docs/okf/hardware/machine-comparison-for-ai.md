---
source_file: ChatGPT-Machine Comparison for AI.md
sha256: d32d7a644b3f5c728fe6c884446909f5d586997067c05129c986a23e54e2db3d
topics: [hardware, machine-comparison, gpu, cost, vast-ai]
related_okf:
  - hardware/rtx-3090-throughput.md
  - hardware/model-improvements-under-500.md
  - benchmarks/model-inference-costs-2026.md
evidence_class: L
status: stub — N10 in-order
---

# Machine Comparison for AI

**Source:** `ChatGPT-Machine Comparison for AI.md` (308 KB) — class **L**.

Vast.ai GPU listings compared on **$/TFLOP, VRAM/$, and DLP tradeoffs** — the corpus enumerates 3090 Ti vs 4090 vs A100 on cost per verified step, not raw tok/s. The matrix is the same cost engine `costengine/calculator.go` evaluates for `config/desktop_nvidia_qwen35_lane.yaml` partitioning (4070 12GB + 1080 8GB).

## Key insight

- Machine choice is **evidence cost**, not hardware lust — `$500` harness budget (see `model-improvements-under-500.md`) maps `rtx-3090-throughput.md` `tok/hour` to `$/verified-step`; Vast.ai $0.39/hr vs local power/host is the `config/eval_pillars.yaml` `cost` pillar.

**Evidence:** `local://sha256/d32d7a644b3f5c728fe6c884446909f5d586997067c05129c986a23e54e2db3d`
