---
source_file: ChatGPT-Machine Comparison for AI.md
sha256: d32d7a644b3f5c728fe6c884446909f5d586997067c05129c986a23e54e2db3d
topics: [benchmarks, hardware, cost, inference]
related_okf:
  - hardware/rtx-3090-throughput.md
  - benchmarks/model-inference-costs-2026.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Machine Comparison for AI

**Source:** `ChatGPT-Machine Comparison for AI.md` (308 KB, 2026-07-04) — sha `d32d7a64` — class **L**.

Benchmark hardware selection: Vast.ai GPU listings, $/TFLOP tradeoffs, and local vs cloud routing for pheno-harness evals.

## Key insights (stub)

- Vast.ai listings show 3090 at $0.35/hr vs A100 at $1.20/hr; 3090 wins $/TFLOP for 8B dense inference (verify vs `hardware/rtx-3090-throughput.md`).
- Machine comparison maps to `config/heterogeneous_tournament.yaml` worker tiers — pairwise sampling reduces machine×model matrix 70% (see benchmarks/pairwise-test-case-generation.md).
- Eval must capture $/verified_pass, not just tok/s — link to `bench/contracts/CELL_PASS_METRICS.md`.

## Next (N10)

- Extract [L] claims with `local://sha256/d32d7a644b3f5c...` citations.
- Verify vs primary Vast.ai pricing and local 3090 rental safety (see gpu-rentals-safety-review.md).
- Promote to [P] after primary source verification before `docs/specs/`.

**Evidence:** `local://sha256/d32d7a644b3f5c728fe6c884446909f5d586997067c05129c986a23e54e2db3d` (class **L**).
