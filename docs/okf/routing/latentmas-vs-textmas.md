---
source_file: ChatGPT-LatentMAS vs TextMAS comparison (1).md
sha256: 8f7689f5581e7db8310912269c15fffbd0b6e09255fdd19bc8cc74abce0e0d0e
topics: [routing, multi-agent, LatentMAS, TextMAS, KV-cache, hidden-states]
related_okf:
  - agents/coding-agents-intent-graphs.md
  - hardware/rtx-3090-throughput.md
  - inference/vram-scaling-factors.md
evidence_class: L
---

# LatentMAS vs TextMAS

LatentMAS moves multi-agent collaboration from serialized text into **last-layer hidden states and shared KV caches** (training-free, same HuggingFace backbone); TextMAS needs only API text in/out. KV/hidden manipulation is **black-boxed on closed hosted APIs** (GPT, GLM-4.6)—LatentMAS requires owning the inference stack with co-located agents. On paper (Qwen3-14B hierarchical MAS), LatentMAS beats TextMAS on MBPP+/HumanEval+ by **+2.5–5.4 accuracy points**, cuts **~80–85% output tokens**, and runs **~3–4× faster** than TextMAS at similar single-agent latency—making a **3090 Ti + Qwen2.5-Coder-14B Q4** local MVP rational if gains replicate; hybrid cloud baselines use GLM-4.6 TextMAS only as comparison oracle, not backbone.

## Key insights

- **Deployment constraint:** LatentMAS needs hidden states, embedding alignment (`W_out⁻¹ W_in`), and KV read/write across agents in one serving process; cloud APIs expose neither (Azure: internal states never leave secure inference).
- **TextMAS advantage:** network/API-only orchestration works on any hosted frontier model; no hardware/environment sharing.
- **Paper numbers (same backbone, hierarchical):** LatentMAS 86.6% vs TextMAS 84.1% (MBPP+); 86.5% vs 81.1% (HumanEval+); ~80–84% fewer output tokens; ~3–4× wall-clock vs TextMAS.
- **Local MVP stack:** Qwen2.5-Coder-14B-Instruct Q4_K_M on 3090 Ti (24 GB); HF backend only in Gen-Verse/LatentMAS repo; `--latent_steps 20–40`, hierarchical prompts.
- **Agent roles:** Architect (plan + KV stash) → Coder (latent rollouts, decode patches) → Tester/tools (deterministic) → Refiner → Summarizer; LLM↔tool edges stay text/JSON.
- **Scale-up tier:** Qwen2.5-Coder-32B on rented A6000/A100 at **<$2/h** when local 14B insufficient; compare against GLM-4.6 TextMAS token cost.
- **Promotion bar:** require ≥+2–5 accuracy vs TextMAS, ~70–80% token reduction, ~3× speedup on real repo tasks—not token reduction alone; keep heterogeneous agents textual per harness policy.
- **Hybrid when frontier quality needed:** local LatentMAS workers + sparse GLM-4.6 planner/reviewer/oracle calls.

## Pheno-harness links

- [`plans/2026-07-14-usch-heterogeneous-inference-v1/ACCELERATION_READINESS.md`](../../plans/2026-07-14-usch-heterogeneous-inference-v1/ACCELERATION_READINESS.md) — LatentMAS gated as research orchestration A/B; same-backbone only; measure code/tool outcomes.
- [`config/heterogeneous_tournament.yaml`](../../config/heterogeneous_tournament.yaml) — `private_chatgpt_corpus` forbidden on mobile workers (corpus isolation).
- [`plans/2026-07-14-usch-heterogeneous-inference-v1/EXPERIMENT_AND_DISCOVERY_PLAN.md`](../../plans/2026-07-14-usch-heterogeneous-inference-v1/EXPERIMENT_AND_DISCOVERY_PLAN.md) — MAS routing experiments.
- [`docs/specs/003-model-engine-matrix.md`](../../specs/003-model-engine-matrix.md) — local tier bands and cloud baseline policy.

**Evidence:** `local://sha256/8f7689f5581e7db8310912269c15fffbd0b6e09255fdd19bc8cc74abce0e0d0e` (class **L**; verify against arXiv 2511.20639 and Gen-Verse/LatentMAS before **P**).
