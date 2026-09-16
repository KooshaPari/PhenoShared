# ForgeCode eval + profiling program — INDEX

Date: 2026-07-03
Status: **Stage 1 plan only.** No code changes have been made.
Reading order: RESEARCH_AUDIT → EVAL_ARCHITECTURE → MODEL_MATRIX →
TRACE_EVALSET_PLAN → IMPLEMENTATION_PLAN → RISKS.

| File | One-line purpose |
|---|---|
| `RESEARCH_AUDIT.md` | Verified facts (with citations) and concrete inventory of what already exists in pheno-harness. |
| `EVAL_ARCHITECTURE.md` | Suite taxonomy, score planes (semantic / harness / serving), trace schema, garden model, performance profiler design. |
| `TRACE_EVALSET_PLAN.md` | How multi-source agent traces are normalized, featurized, and scored per role across 8 canonical roles. |
| `MODEL_MATRIX.md` | Tiered candidate model list (0.4B→35B), engine coverage (ik_llama / SGLang / vLLM / TRT-LLM / MLX / BitNet), 3090 Ti fitting, M1 Pro fallback. |
| `IMPLEMENTATION_PLAN.md` | Staged PR plan (PR-1..PR-10), CI gates, chat-loop gate set (G1..G7), self-improvement loop, intent-graph sketch. |
| `RISKS.md` | 20 enumerated risks, each with detection signal and automatic action. |

---

## TL;DR (the 30-second version)

Pheno-harness already implements roughly **70%** of the brief's asks.
Concrete:

- **TB2.0 + terminus-2 leaderboard** is wired (`eval/tbench.py`).
- **OmniRoute combo routing** is wired (`config/combo_main.json`).
- **ik_llama-server swarm** (Qwen4B + 0.6B draft) is wired
  (`pheno/model_manager.py`).
- **Multi-source trace ingest** is wired (`traces/ingest.py`).
- **RLVR + risky-action gate** is wired (`verifier/`).
- **Composite scoring 40/30/30** is wired (`eval/route_matrix.py`).
- **Self-improvement loop** is half-wired (nightly_dpo, distill_12b,
  train_sub1b), but it is a chain, not a garden.

The plan fills the **30% gap**:

1. DeepSWE + SWE-bench Verified / Lite — new suites.
2. Per-role trace-derived evalset — new pipeline.
3. Real performance profiler (TTFT, ITL, ctx-cache, queue, harness
   overhead, N-agent sweeps).
4. Engine adapters — SGLang, vLLM, TRT-LLM, MLX, custom CUDA.
5. Intent-graph / scheduler refactor (chat-loop → planner DAG).
6. Garden model — multi-signal reward, gates, authorship audit,
   automatic demotion.
7. M1 Pro fallback (MLX) for the secondary machine.

The plan is **stage 1 only**. Stage 2 (codex fork) is gated by stage 1
landing green (`IMPLEMENTATION_PLAN.md` §5 ladder).
