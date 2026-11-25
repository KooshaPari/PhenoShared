---
source_file: ChatGPT-Agent-Aware Speculative Decoding.md
sha256: 40367eafa68468ff0b8e4c58101d5437e4793997aebaa6d3a1dcdeb29ac5e5dc
topics: [speculative-decode, inference, agents, JetSpec, DDTree, EAGLE, PEARL, DFlash]
related_okf:
  - inference/vram-scaling-factors.md
  - hardware/rtx-3090-throughput.md
  - routing/latentmas-vs-textmas.md
  - agents/coding-agents-intent-graphs.md
evidence_class: L
---

# Agent-Aware Compound Speculative Decoding

Speculative decoding has converged from “small draft model guesses tokens” into a compound design space—parallel tree drafting, block-diffusion drafters, adaptive verify scheduling, and harness-level routing—where the optimal policy depends on task type, model, hardware, and live acceptance telemetry rather than a single global winner. The corpus synthesizes JetSpec (causal parallel tree drafting), DDTree/CaDDTree (block-diffusion draft trees), PEARL (draft/verify overlap), P-EAGLE/EAGLE 3.1 (feature-level and parallel drafting), and DFlash (one-pass block proposals) into a unified **CandidateGraph → VerifyPolicy → Scheduler** interface and a proposed **CASCADE** system that routes proposers per agent workload segment (code, JSON/tool calls, boilerplate, reasoning).

## Key insights

- **Unified interface:** All methods map to `DraftPolicy → CandidateGraph → VerifyPolicy → Scheduler(telemetry)`; candidates are graphs (nodes, causal edges, scores, masks), not flat token sequences.
- **Regime-specific winners:** n-gram/suffix + repo cache for boilerplate; EAGLE/P-EAGLE for general coding; JetSpec-style causal trees for math/code branches; DFlash/DDTree for parallel block uncertainty; PEARL overlap when draft/verify bubbles appear; disable or shrink speculation at high-entropy tool-call boundaries.
- **Agent harness priors:** Task-type hints (code vs JSON vs shell vs diff), acceptance-contract telemetry, and repo-local proposal caches (paths, imports, stack traces) are decoding priors—not just correctness artifacts.
- **CASCADE modules:** Telemetry collector, multiple proposal backends, target verifier with tree attention, rule→bandit router, and harness integration that switches policy at segment boundaries.
- **Phased implementation:** Start with vanilla draft + n-gram + EAGLE in vLLM/SGLang + telemetry; add segment router and repo suffix cache; then tree abstractions (DDTree/JetSpec); finally bandit router tied to acceptance contracts.
- **Agent metrics beyond tok/s:** patch completion latency, JSON/tool-call validity, repo edit wall-clock, agent loop turns per dollar, and exact distribution preservation.
- **Research claim:** Speculative decoding for agents is a **harness-level** optimization; the orchestrator knows schema constraints, repo state, and task boundaries that generic chat serving ignores.

## Pheno-harness links

- [`docs/specs/003-model-engine-matrix.md`](../../specs/003-model-engine-matrix.md) — cites this corpus; lists EAGLE/P-EAGLE/N-gram/suffix/MLP-draft as permitted optimizations on 3090 Ti.
- [`config/inference_runners.yaml`](../../config/inference_runners.yaml) — DFlash speculative config on vLLM control lane.
- [`plans/2026-07-14-usch-heterogeneous-inference-v1/ACCELERATION_READINESS.md`](../../plans/2026-07-14-usch-heterogeneous-inference-v1/ACCELERATION_READINESS.md) — JetSpec, DDTree/CaDDTree, DFlash, native MTP gated behind production baselines.
- [`plans/2026-07-14-usch-heterogeneous-inference-v1/MODEL_RUNTIME_MATRIX.md`](../../plans/2026-07-14-usch-heterogeneous-inference-v1/MODEL_RUNTIME_MATRIX.md) — SGLang primary / vLLM control on 3090 Ti before research spec paths.

**Evidence:** `local://sha256/40367eafa68468ff0b8e4c58101d5437e4793997aebaa6d3a1dcdeb29ac5e5dc` (class **L**; verify against arXiv/GitHub before promotion to **P**).
