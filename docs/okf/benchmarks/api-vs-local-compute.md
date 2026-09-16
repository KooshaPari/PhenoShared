---
source_file: ChatGPT-API vs Local Compute.md
sha256: placeholder-api-vs-local-compute
topics: [benchmarks, api, local-compute, routing]
related_okf:
  - routing/latentmas-vs-textmas.md
  - benchmarks/pairwise-test-case-generation.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# API vs Local Compute

**Source:** `ChatGPT-API vs Local Compute.md` — class **L**.

API vs local tradeoffs: latency, cost, privacy, and benchmark design for hybrid routing.

## Key insights (stub)

- Local 3090 viable for <8B models; API for >70B. Pairwise routing eval covers api×local×model.
- Forward DAG N10 uses pairwise to reduce api vs local combos.

## Next (N10)

- Extract [L] claims and map to `bench/adapters.py` routing logic.
- Verify vs primary cost benchmarks.

**Evidence:** `local://sha256/placeholder-api-vs-local-compute` (class **L**).
