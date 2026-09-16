---
source_file: ChatGPT-User-level Deterministic Cache.md
sha256: 3821fd75d9dc1e7b81642e7c4b592f941f8662c11ccf33f550a6fd31ce2562b0
topics: [benchmarks, caching, determinism, eval]
related_okf:
  - inference/agent-aware-speculative-decoding.md
  - benchmarks/pairwise-test-case-generation.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# User-level Deterministic Cache

**Source:** `ChatGPT-User-level Deterministic Cache.md` (862 KB, 2026-07-04) — sha `3821fd75` — class **L**.

Benchmark caching strategy: user-level deterministic cache for KV reuse, TTFT/TPOT tradeoffs, and verified_pass impact.

## Key insights (stub)

- Deterministic cache improves TTFT 30–40% for repeated prompts; benchmark must isolate cache hit vs miss (see `bench/suites/`).
- Cache benchmark links to `pheno/evidence/adapters/local_corpus.py` hash-only scheme — no path leakage.
- Pairwise test generation helps cover cache×model×prompt variants efficiently.

## Next (N10)

- Extract [L] claims with `local://sha256/3821fd75d9dc1e...` citations.
- Map to `bench/matrix` cache model and `config/eval_pillars.yaml`.
- Promote to [P] after primary cache literature verification.

**Evidence:** `local://sha256/3821fd75d9dc1e7b81642e7c4b592f941f8662c11ccf33f550a6fd31ce2562b0` (class **L**).
