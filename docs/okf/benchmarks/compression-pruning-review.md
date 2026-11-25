---
source_file: ChatGPT-Compression Pruning Review.md
sha256: placeholder-compression-pruning-review
topics: [benchmarks, compression, pruning, eval]
related_okf:
  - inference/vram-scaling-factors.md
  - hardware/rtx-3090-throughput.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Compression Pruning Review

**Source:** `ChatGPT-Compression Pruning Review.md` — class **L**.

Benchmarks for compression/pruning: sparsity vs accuracy tradeoffs, hardware-aware eval.

## Key insights (stub)

- 50% pruning retains 95% accuracy on MMLU-pro for 8B models; verify on bench/suites/mmlu_pro.py.
- Pairwise sampling can cover compression levels efficiently.

## Next (N10)

- Extract claims and map to `bench/bench.py` compression variants.
- Verify vs primary pruning literature.

**Evidence:** `local://sha256/placeholder-compression-pruning-review` (class **L**).
