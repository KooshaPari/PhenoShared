---
source_file: ChatGPT-Feature graph system design.md
sha256: 2480042c654da12cbea11289055314275469d037f3da731de5fdfd47b0c30b58
topics: [agents, feature-graph, system-design, intent-graph, traceability]
related_okf:
  - agents/coding-agents-intent-graphs.md
  - routing/latentmas-vs-textmas.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Feature Graph System Design

**Source:** `ChatGPT-Feature graph system design.md` (188 KB, 2026-07-04) — class **L**.

Feature graphs treat product intent as a **node-typed DAG** where features, constraints, and verification criteria are first-class nodes with explicit edges (depends-on, enables, conflicts). Unlike flat backlogs, the graph compiler can **prune, specialize, and patch** subgraphs when discovery (repo facts, eval failures, API shapes) invalidates assumptions — the same `intent-graph → compiler → dumb executor` pattern from `coding-agents-intent-graphs.md`, applied to system-level feature decomposition.

## Key insights (stub — full distillation pending N10)

- **Node types:** feature objective, expected outputs/evidence, tool calls, confidence, invalidation rules — mirrors intent-graph schema.
- **Edge semantics:** dependency (hard), enablement (soft), conflict (mutex) — enables topological scheduling across lanes (B: serve/eval, C: hand-roll/x-perf, A: knowledge/spec).
- **Compiler pass:** inspection subgraphs (repo fact-finders) rewrite downstream nodes before weak executors run — avoids regenerate-from-scratch loops.
- **Verification:** each feature node carries acceptance contracts (cf. `EVALUATOR_CONTRACT.md`) so `harbor_evaluate.sh` can check `result.json` against graph expectations.
- **Pheno-harness link:** feature graphs are the **planning artifact** for Forward DAG v2 itself (N01→N25) — this OKF page closes the loop between corpus theory and `plans/2026-07-24-forward-dag-v2/INDEX.md`.

## Next (N10)

- Extract full `[L]`-tagged claims with `local://sha256/2480042c...` citations.
- Add cross-links to `docs/okf/routing/*` and `plans/2026-07-24-forward-dag-v2/INDEX.md` §2 (DAG nodes as feature-graph instances).
- Verify against primary sources (HF, arXiv) before promoting to **P** and to `docs/specs/`.

**Evidence:** `local://sha256/2480042c654da12cbea11289055314275469d037f3da731de5fdfd47b0c30b58` (class **L**).
