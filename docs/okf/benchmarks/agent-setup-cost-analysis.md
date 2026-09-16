---
source_file: ChatGPT-Agent Setup Cost Analysis.md
sha256: placeholder-agent-setup-cost-analysis
topics: [benchmarks, agents, setup-cost, harness]
related_okf:
  - benchmarks/pairwise-test-case-generation.md
  - agents/coding-agents-intent-graphs.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Agent Setup Cost Analysis

**Source:** `ChatGPT-Agent Setup Cost Analysis.md` — class **L**.

Harness setup costs: container provisioning, tool installation, and per-trial overhead for harbor/terminal-bench.

## Key insights (stub)

- Setup cost dominates short trials; amortize via shared reservation (see bench/batch_manifest_2026-08-19.yaml).
- Pairwise sampling reduces setup cost 70% by sharing base images.

## Next (N10)

- Extract [L] claims and link to `scripts/pheno_eval_batch.py` reservation model.
- Verify vs primary harbor provisioning docs.

**Evidence:** `local://sha256/placeholder-agent-setup-cost-analysis` (class **L**).
