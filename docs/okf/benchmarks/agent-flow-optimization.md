---
source_file: ChatGPT-Agent Flow Optimization.md
sha256: 646a4d05feb934ce2765e3368cafeb3fff21e895bafe6d9075a1dd7c450ac502
topics: [benchmarks, agents, flow, orchestration]
related_okf:
  - agents/coding-agents-intent-graphs.md
  - benchmarks/pairwise-test-case-generation.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Agent Flow Optimization

**Source:** `ChatGPT-Agent Flow Optimization.md` (49 KB, 2026-07-04) — sha `646a4d05` — class **L**.

Benchmark agent flow: orchestration latency, tool-call stability, and harness setup cost for harbor/terminal-bench evals.

## Key insights (stub)

- Flow optimization reduces per-trial overhead 25% via shared reservation (see bench/batch_manifest_2026-08-19.yaml).
- Benchmark should measure flow×model×route pairwise matrix — 6 routes × 89 tasks → ~40 representative trials.
- Links to `routing/latentmas-vs-textmas.md` KV-sharing MAS vs API TextMAS tradeoff.

## Next (N10)

- Extract [L] claims with `local://sha256/646a4d05feb934...` citations.
- Verify vs primary harbor provisioning docs and `scripts/pheno_eval_batch.py`.
- Promote to [P] after primary source verification.

**Evidence:** `local://sha256/646a4d05feb934ce2765e3368cafeb3fff21e895bafe6d9075a1dd7c450ac502` (class **L**).
