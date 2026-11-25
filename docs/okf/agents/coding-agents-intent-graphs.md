---
source_file: ChatGPT-Coding Agents and Intent Graphs (1).md
sha256: b593aa9ebd32002389ef7e8deb3cff790193a7bb135c5d50ab79531d16bcb1ed
topics: [agents, intent-graph, orchestration, scheduler, tool-calls, escalation]
related_okf:
  - routing/latentmas-vs-textmas.md
  - inference/agent-aware-speculative-decoding.md
evidence_class: L
---

# Coding Agents and Intent Graphs

Coding agents fail to deliver “intent graph → dumb executor” not because graphs are impossible, but because repo work is discovery-heavy and most harnesses are chat loops without a compiler, scheduler, or invalidation layer to keep plans valid as observations arrive. The corpus argues for a **progressively specialized intent DAG**: strong planner emits a first-draft graph with objectives, expected tool calls, confidence, and invalidation rules; inspection subgraphs bind concrete files/symbols; a graph compiler prunes or specializes downstream nodes; weak models and deterministic tools execute leaves; divergence between predicted and actual tool paths triggers local replan or escalation to a strong reviewer—**Bazel/Ninja for agent intent**, not ReAct chat.

## Key insights

- **Why static plans fail:** Steps depend on API shapes, test failures, build quirks, and stale docs discovered after the first few observations—plans must **patch**, not regenerate wholesale.
- **Layered graphs:** `exploration → repo facts → implementation → execution → verification → review`, where inspection is itself a subgraph whose output rewrites later nodes.
- **Node schema:** objective, expected outputs/evidence, expected tool calls, confidence, invalidation conditions—enabling programmatic pruning when inspection finds existing auth infra, etc.
- **Execution split:** strong model for decomposition and escalation; weak/non-AI executor for grep, read, test, simple edits; strong re-entry on semantic test failures, patch conflicts, or confidence drops.
- **Prediction-market signal:** compare expected vs actual tool paths; divergence scores whether to continue, replan a subtree, or escalate—richer supervision than prompt→answer pairs.
- **Product framing (ForgeGraph / intent-graph runtime):** primary artifact is the graph; LLMs are services attached to nodes; differentiator vs Claude Code/ReAct is compile-once + patch, not plan→execute loops every turn.
- **Blockers today:** lazy prose planners, no typed pre/postconditions, weak models that don’t know when they’re wrong, brittle edit tool calls, and hard context-bundle assembly for parallel search.

## Pheno-harness links

- [`plans/2026-07-14-usch-heterogeneous-inference-v1/EVALUATOR_CONTRACT.md`](../../plans/2026-07-14-usch-heterogeneous-inference-v1/EVALUATOR_CONTRACT.md) — acceptance contracts align with graph node success criteria.
- [`config/harbor_tbench_pheno_serve.yaml`](../../config/harbor_tbench_pheno_serve.yaml) — agent serving profiles on 3090 Ti hardware.
- [`plans/2026-07-14-usch-heterogeneous-inference-v1/ACCELERATION_READINESS.md`](../../plans/2026-07-14-usch-heterogeneous-inference-v1/ACCELERATION_READINESS.md) — LatentMAS/TextMAS orchestration A/B gated to same-backbone runs.
- [`docs/specs/003-model-engine-matrix.md`](../../specs/003-model-engine-matrix.md) — tiered model lanes for planner vs worker vs escalation.

**Evidence:** `local://sha256/b593aa9ebd32002389ef7e8deb3cff790193a7bb135c5d50ab79531d16bcb1ed` (class **L**).
