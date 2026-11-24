---
source_file: ChatGPT-Compression Pruning Review (1).md
sha256: 436a355bcfba341c8712edd33f3760babb2766862913014a7ec5cab86d434843
topics: [inference, compression, pruning, quantization, sparsity, benchmarks]
related_okf:
  - inference/vram-scaling-factors.md
  - hardware/rtx-3090-throughput.md
  - benchmarks/model-inference-costs-2026.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Compression Pruning Review

**Source:** `ChatGPT-Compression Pruning Review (1).md` (1,245,244 bytes, 2026-06-13) — sha `436a355b` — class **L**.

Benchmark compression/pruning: sparsity vs accuracy tradeoffs, quantization-aware pruning, and hardware-aware eval for 8B dense and MoE serving on 24 GB VRAM.

## Key insights (stub)

- 50% unstructured pruning retains ~95% accuracy on MMLU-pro for 8B models at Q4; 2:4 structured sparsity maps to ~1.3× decode uplift on Ampere (verify on `bench/suites/mmlu_pro.py` and `kernels/qwen3.5-0.8b/metal/`).
- Hardware-aware eval must track $/verified_pass not just tok/s — pruning reduces KV and weight bandwidth but incurs dequant overhead; link to `bench/contracts/CELL_PASS_METRICS.md`.
- Pairwise sampling can cover compression levels efficiently (see `benchmarks/pairwise-test-case-generation.md`).

## Next (N10)

- Extract [L] claims with `local://sha256/436a355bcfba341c8712edd33f3760babb2766862913014a7ec5cab86d434843` citations.
- Verify vs primary pruning literature (SparseGPT, Wanda, AWQ) and `bench/bench.py` compression variants before promotion to [P].
- Map to `docs/specs/` only after primary-source verification.

**Evidence:** `local://sha256/436a355bcfba341c8712edd33f3760babb2766862913014a7ec5cab86d434843` (class **L**).
