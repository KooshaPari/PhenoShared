---
source_file: ChatGPT-GPU Rentals Safety Review.md
sha256: db67d55b180a30d4283f7fe3e040c2fe3bea4afa933d0a15359deb1ed292ab4e
topics: [benchmarks, hardware, rental, safety]
related_okf:
  - benchmarks/machine-comparison-for-ai.md
  - benchmarks/ai-inference-hardware-costs.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# GPU Rentals Safety Review

**Source:** `ChatGPT-GPU Rentals Safety Review.md` (43 KB, 2026-06-14) — sha `db67d55b` — class **L**.

Benchmark rental safety: Vast.ai / RunPod trust, preemption risk, and $/verified_pass impact for harbor evals.

## Key insights (stub)

- Rental preemption adds 8–15% effective cost for long trials; benchmark must model restart overhead (see `bench/runner/executor.py`).
- Safety eval covers provider SLA vs local 3090 reliability — maps to `config/disk_budget_2026-07.yaml` watchdog.
- Pairwise sampling reduces exposure by sharing reservations (see benchmarks/pairwise-test-case-generation.md).

## Next (N10)

- Extract [L] claims with `local://sha256/db67d55b180a30...` citations.
- Verify vs primary Vast.ai / RunPod docs and `scripts/pheno_eval_batch.py` reservation model.
- Promote to [P] after primary source verification.

**Evidence:** `local://sha256/db67d55b180a30d4283f7fe3e040c2fe3bea4afa933d0a15359deb1ed292ab4e` (class **L**).
