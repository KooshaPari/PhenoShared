# ADR 0001 — Current-State Audit

> **Status:** Evidence-backed snapshot as of 2026-07-03. Immutable except for
> corrections in a follow-up ADR.
> **Purpose:** Lock down the current state of the world before designing/implementing the eval + profiling program on top of `pheno-harness` (and later `codex-dev`).
> **Author scope:** Forge, running as the senior research+systems coding agent. No files in `pheno-harness/` were mutated by this audit; this is a read-only artifact.
> **Naming convention:** the owned forks use the `-dev` suffix in their bin/path names — `forge-dev`, `omniroute-dev`, `codex-dev` — as fixed in `docs/ARCHITECTURE_LAYERS.md`. The layer model also includes `pheno-serve-dev` (inner inference router) below `omniroute-dev` and above the concrete engines.

---

## 0. TL;DR

1. The brief's "forked ForgeCode" starting point (`~/forge-dev`) does not exist locally. The actual work surface is `~/pheno-harness`, which already contains a substantially-complete version of the program the brief describes (Harbor TB2 driver, route matrix, pillar scoring, budget gates, trace ingest, MoE/risky-action governance, ik_llama local swarm, RLVR-AF scaffolding). Plan builds **on** what's there; it does not replace it.
2. Primary-source check is complete for: Harbor, Terminal-Bench 2.0/2.1/3.x, DeepSWE, OpenRouter `inclusionai/ling-2.6-flash`, vLLM prefix-cache + speculative-decoding, SGLang, TensorRT-LLM.
3. The corpus in `D:\koosh\Downloads\ChatGPT-*.md` is broadly aligned with the live sources on MoE economics, serving-stacks, 3090 Ti sizing, RLVR-AF, intent graphs, agent-aware speculative decoding, and user-level deterministic caches. A few numbers from the corpus are stale (model SKUs, pricing) — flagged inline.
4. **Gaps vs brief** are concentrated in four places: DeepSWE / SWE-bench Verified integration, **a real performance-profiling suite** (CPU/RAM/VRAM/disk/TTFT/ITL/queue/cache), local model+engine matrix with vLLM/SGLang/TRT-LLM/llama.cpp/MLX coverage, and the **architectural transition from chat-loop → intent-graph scheduler**. These are the design problems for the next phase.

---

## 1. Local code-root inventory (Windows)

Verified with `dir /b` and explicit `if exist` checks.

| Path | Status | What it actually is |
|---|---|---|
| `~/forge` | exists | Global Forge home. `AGENTS.md`, `.forge.toml`, `crates/{forge-cli, forge-runner, governance-resolver, prompt-library, skill-manifest}`, `skills/`, `agents/`, `commands/`. **No `forgecode` source tree inside it.** |
| `~/pheno-harness` | exists | Real, structured scaffold. Pre-existing version of this program. Submodule `agileplus-specs/` (per `.gitmodules`-style reference in AGENTS.md; not checked-in here, see §6 unknowns). |
| `~/pheno-specs` | **missing locally** | Brief mentions it; AGENTS.md says pheno-harness submodules it. The actual local name is `agileplus-specs/`. |
| `~/forge-dev` | **missing locally** | Brief's stated starting point. Does not exist as a fork. The coding-agent side lives at `~/forge` (global Forge home: `AGENTS.md`, `.forge.toml`, `crates/{forge-cli, forge-runner, governance-resolver, prompt-library, skill-manifest}`). The owned fork's planned bin/path identity is `forge-dev` per `docs/ARCHITECTURE_LAYERS.md`. |
| `~/codex-work` | empty | Brief mentions moving to a `codex-dev` fork later. Currently an empty dir. Stage 2 (codex fork work) is gated on user sign-off. |
| `~/omniroute-dev` | exists but junk locally | Contains log dumps, not the router. The "OmniRoute Main blend" referenced in `pheno-harness/config/combo_main.json` is config-only locally; the actual router is on the remote side. Owned fork identity: `omniroute-dev` per `docs/ARCHITECTURE_LAYERS.md`. |
| `~/pheno-serve-dev` | **missing locally** | New layer in scope this round — inner inference router (engine lifecycle, OpenAI-compat endpoint per engine). Per `docs/ARCHITECTURE_LAYERS.md` it sits below `omniroute-dev` and above concrete engines. See `docs/adrs/0003-local-serving-bootstrap.md` for the bootstrap plan. |
| `~/pheno-harness/docs/{adrs,specs}/` | **newly created** | Home for this audit, the rest of the deliverables in this round, and all future ADRs / specs. Canonical: `SPEC.md`, `DESIGN.md`, `docs/README.md`. |

Implication: the program description in the brief maps onto the existing `pheno-harness` skeleton almost 1:1. The next phase adds depth in the gaps, not a new repo.

---

## 2. What `pheno-harness` already provides (citable surfaces)

Cited against real files in `pheno-harness/`. Numbers/lines as observed on 2026-07-03.

### 2.1 Eval + scoring

- `pheno-harness/eval/tbench.py` — Harbor TB2 driver; terminus-2 agent; `n_attempts=1` honest eval; excludes TB2 holdout from `nightly_dpo`.
- `pheno-harness/eval/route_matrix.py` — composite score **40 % accuracy / 30 % speed / 30 % cost**; route kinds `omniroute_cloud | local_direct | omniroute_combo`.
- `pheno-harness/eval/pillars.py` + `config/eval_pillars.yaml` — 7-pillar scoring (correctness, efficiency, determinism, safety, robustness, latency, cost).
- `pheno-harness/eval/budget.py` + `config/budget_targets.yaml` — cost accounting.
- `pheno-harness/eval/nested_rlvr.py` — L0/L1/L2/L3 ladder, soft-SVeRL, MR-RLVR stacking.
- `pheno-harness/eval/HARBOR.md` — internal Harbor notes; **does not yet mention TB 2.1** (see §3.2 below).
- `pheno-harness/eval/results/` — already has `tbench_model_scores.json`, `tbench_route_probe.json`, `wastage_latest.json`, `budget_latest.json`, `harbor_latest.json`. Format used as the schema template for new suites.

### 2.2 Governance / config layer

- `pheno-harness/config/eval_pillars.yaml` — pillar weights + thresholds.
- `pheno-harness/config/inference_runners.yaml` — **SGLang primary**, vLLM secondary, llama-server legacy, BitNet for sub-1B drafts. TensorRT-LLM is marked `not_recommended_primary` due to compile overhead.
- `pheno-harness/config/models.yaml` + `local_model_bench_matrix.yaml` — local tier matrix (0.6B draft, 4B main, on-demand swap).
- `pheno-harness/config/decode_acceleration_matrix.yaml` — prefix cache / chunked prefill / spec-dec policies.
- `pheno-harness/config/moe_deploy_policy.yaml` — MoE activation + VRAM rules.
- `pheno-harness/config/risky_action_gate.yaml` — gates destructive actions in eval sandboxes.
- `pheno-harness/config/activation_edit_policy.yaml` — activation-edit training/inference policy.
- `pheno-harness/config/context_caps.yaml`, `budget_targets.yaml`, `role_lora.yaml`, `cloud_tiers.yaml`, `combo_main.json`, `local_swarm.yaml`.
- `pheno-harness/harness/lanes.yaml` — role lanes (`routine`, `ci`, `architecture`, `medium_hard`, `research`) with provider binding (claude-opus-4-8 via forge, MiniMax M3, Cursor composer, etc.).
- `pheno-harness/config/harbor_tbench_models.yaml` + `harbor_tbench_routes.yaml` + `harbor_tbench_agent.yaml` — Harbor config (TB2 leaderboard + route kinds).
- `pheno-harness/config/repo2rl.yaml`, `kv_bakeoff.yaml`, `playground_matrix.yaml`.

### 2.3 Traces + RLVR

- `pheno-harness/traces/{ingest, motion, wastage}.py` — multi-source ingest (OmniRoute SQLite, forge history, codex, claude, cursor, factory droid).
- `pheno-harness/verifier/{harness, rewards, risky_action}.py` — RLVR scoring + risky-action gating.
- `pheno-harness/training/{rlvr_config, distill_12b, draft_06b, eval_holdout, nested_rlvr, sub1b_needle}.yaml` — training recipes.

### 2.4 Scripts (CLI surface)

`scripts/run_tbench_route_matrix.py`, `run_playground.py`, `run_eval_suite.py`, `run_tbench_model_matrix.py`, `tbench_scoreboard.py`, `tbench_route_scoreboard.py`, `collect_traces.py`, `analyze_wastage.py`, `repo2rl_{setup,eval}.py`, `kv_bakeoff.py`, `decode_prepare.py`, `moe_prepare.py`, `activation_prepare.py`, `nightly_dpo.py`, `train_sub1b.py`, `distill_12b.py`, `probe_omniroute_models.py`, `probe_tbench_routes.py`, `compile_context.py`, `start_local_swarm.ps1`.

### 2.5 Local inference runtime

- `pheno-harness/pheno/model_manager.py` — ik_llama-based local swarm: Qwen 4B always-on, 0.6B draft, on-demand swap. No vLLM/SGLang/TRT-LLM workers wired in locally.
- `pheno-harness/pheno/harbor_util.py` — Harbor + OmniRoute env wiring.
- `pheno-harness/pheno/{paths, router, __init__}.py` — supporting plumbing.

**Bottom line:** pheno-harness has the eval spine, governance layer, trace ingest, and training recipes. It does **not** have a full serving-engine matrix, a hardware-level performance profiler, an intent-graph scheduler, a DeepSWE driver, SWE-bench Verified regression, or a per-role trace eval pipeline. Those are the design problems.

---

## 3. Primary-source verification (live as of 2026-07-03)

### 3.1 Harbor

- Harbor is the official harness for Terminal-Bench 2.x. Docs: <https://www.harborframework.com/docs/tutorials/running-terminal-bench>. Verified.
- Harbor's GitHub org hosts TB 3.x: <https://github.com/harbor-framework/terminal-bench-3> (1,263 commits, accepted as official).

### 3.2 Terminal-Bench 2.0 / 2.1 / 3.x

- **TB2.0 = 89 tasks** (verified subset, full leaderboard available via Harbor CLI). Pheno-harness's `eval/HARBOR.md` matches.
- **TB2.1 = ACTIVE on tbench.ai** as "improved version, inspired by Z.ai's TB2.0 Verified". **Pheno-harness's `eval/HARBOR.md` does not yet mention TB 2.1.** Plan must add support for `terminal-bench@2.1` in addition to `@2.0`.
- **TB3.0 in active development.** Track both 2.x and 3.x compatibility in `config/harbor_tbench_models.yaml`.
- **TB2.0 leaderboard signal (verified subset, 2026-07-03):**
  - Codex CLI on GPT-5.5 ≈ 0.822
  - Meta-Harness on Claude Opus 4.6 ≈ 0.764
  - Droid (Factory) on GPT-5.3-Codex ≈ 0.773
  - Top of leaderboard ≈ 0.85
  - **Real SOTA target set:** GPT-5.5, Claude Opus 4.6/4.7/4.8, Gemini 3.1 Pro, Ling-2.6-flash-tier open-weight models.

### 3.3 DeepSWE

- Self-described long-horizon SWE benchmark: <https://deepswe.datacurve.ai/>.
- **113 tasks** across TS, Go, Python, JS, Rust. Harbor task format. Verified.
- **Separate verifier since v1.1.** Requires Pier ≥ 0.3.0.
- Models used in published leaderboard: `claude-opus-4-8`, `gpt-5.5`, `gemini-cli` via Pier with `--env modal` for parallel sandboxes.
- Pheno-harness does not yet have a DeepSWE driver. Add to `pheno-harness/eval/deepswe.py`.

### 3.4 OpenRouter `inclusionai/ling-2.6-flash`

- **104B total / 7.4B active MoE**, agent-oriented. Verified via OpenRouter model page.
- **Context window: 262,144 tokens** (specific large number, not "long context"). Brief was vague; this is the verified value.
- **Pricing (verified, 2026-07-03):** $0.01 in / $0.03 out per 1M tokens (90 % promo). Brief's "$0.56/$2.49" was an older tier; do not use.
- Released 2026-04-21.
- Recommended deployment in pheno-harness: route kind `omniroute_cloud`, lane `medium_hard` (already mapped), bound to this exact model id in `config/models.yaml` (verify the spelling on every PR — model id drift is a real failure mode here).

### 3.5 Artificial Analysis Coding Agent Index

- Composite of DeepSWE + Terminal-Bench v2 + SWE-Atlas-QnA. Use as a comparison signal, not as the sole target. We re-run the components ourselves so we can decompose the signal.

### 3.6 vLLM (verified)

- **Prefix caching:** block-allocated, LRU, with documented operations. <https://docs.vllm.ai/en/stable/design/prefix_caching/>.
- **Speculative decoding:** draft-model, dynamic spec-dec, EAGLE, MTP, N-gram, Suffix, Speculators library, MLP draft, parallel draft. <https://docs.vllm.ai/en/latest/features/speculative_decoding/>.
- Other confirmed: online serving, OpenAI-compat, codex integration, claude-code integration, KV offloading, LoRA, quantization (AWQ, BnB, FP8, GGUF, GPTQModel, ModelOpt, NVFP4 on Blackwell, llm-compressor with FP8/INT4/INT8), explicit `profiling` page. All verified.

### 3.7 SGLang

- Explicitly aimed at low-latency / high-throughput serving. <https://docs.sglang.ai/>. Robot-blocked landing scrape but confirmed via mirror; treat as authoritative.
- Pheno-harness's `config/inference_runners.yaml` already names SGLang as primary agent runner — keep.

### 3.8 TensorRT-LLM

- In-flight batching, paged KV cache, speculative decoding, quantization, multi-GPU. <https://nvidia.github.io/TensorRT-LLM/overview.html>.
- Pheno-harness's current yaml marks TRT-LLM `not_recommended_primary` due to compile overhead. Plan must respect that on 3090 Ti (compile time vs. run time is unfavorable) but re-evaluate for Blackwell-class when hardware changes.

---

## 4. Local corpus findings (`D:\koosh\Downloads\ChatGPT-*.md`)

Read on 2026-07-03. Findings the audit pins down vs. flags.

| File | Take-aways | Status |
|---|---|---|
| `ChatGPT-VRAM and Scaling Factors (1).md` | KV-cache dominates VRAM at long context; MoE activation reduces active footprint but total params still need disk + CPU paging strategy. Aligns with live sources. | **Use.** |
| `ChatGPT-RTX 3090 Throughput Analysis.md` | 3090 Ti has 24 GB VRAM, GA102, no FP8 tensor cores; quantization choice matters (AWQ/INT8 strong, FP8 unavailable, NVFP4 unavailable). | **Use, but downgrade any FP8/NVFP4 claims — 3090 Ti doesn't have FP8 tensor cores.** |
| `ChatGPT-LatentMAS vs TextMAS comparison (1).md` | Latent-MAS uses continuous hidden-state communication between agents; cheaper, less inspectable. Text-MAS is what pheno-harness uses today (JSON messages). Useful as a future research direction, not as a near-term build target. | **Note as research direction; do not commit.** |
| `ChatGPT-Compression Pruning Review (2).md` | Activation-aware quantization (AWQ) and GPTQ dominate on consumer GPUs. Sparse methods (SparseGPT, Wanda) less mature for serving. | **Use for quantization choices in MODEL_MATRIX.** |
| `ChatGPT-AI Inference Hardware Costs (1).md` | Aligns with live: M1 Pro is fine for sub-1B drafts and small workers, not for sustained 4B+ throughput. 3090 Ti sweet spot is 4B–12B dense, 30B+ MoE with offload. | **Use for sizing strategy.** |
| `ChatGPT-Efficiency Evolutions Post-MoE (1).md` | Speculative decoding, EAGLE, draft-token methods, prefix cache, chunked prefill are the dominant post-MoE wins. Aligns with live sources. | **Use.** |
| `ChatGPT-RLVR-AF Optimization Proposal (1).md` | "Activate-then-forget" RLVR pattern: train on filtered rollouts where risky actions succeed, then drop the activation during deployment. Already partially implemented in `pheno-harness/config/activation_edit_policy.yaml` + `verifier/risky_action.py`. | **Use; pheno-harness is already on this path.** |
| `ChatGPT-Coding Agents and Intent Graphs (1).md` | Intent-graph > chat loop: planner builds typed DAG, deterministic tools execute leaves, weak/local workers run constrained sub-tasks. **Strong design signal for the next architectural iteration.** | **Use as design north star.** |
| `ChatGPT-Agent-Aware Speculative Decoding.md` | When a planner + sub-agent pattern is in use, draft tokens from the planner can be reused across sub-agents if prefix is shared. Cache hit rate improves materially. | **Use for cache design in MODEL_MATRIX + EVAL_ARCH.** |
| `ChatGPT-Model improvements under $500.md` | Mostly hardware pricing, broadly aligns with `AI Inference Hardware Costs`. | **Light use; treat as cross-check.** |
| `ChatGPT-Machine Comparison for AI.md` | Same as above. | **Light use.** |
| `ChatGPT-Model Inference Costs 2026.md` | Several model SKUs and prices are stale; verify against OpenRouter before quoting. | **Verify before use; do not paste verbatim.** |
| `ChatGPT-Concurrent Lint Command Handling.md` | Suggests deterministic lint/test commands executed by harness, not by LLM. Aligns with intent-graph direction. | **Use as pattern.** |
| `ChatGPT-Feature graph system design.md` | Feature-graph as a DAG of typed nodes, with plan→execute→verify edges. Reinforces intent-graph direction. | **Use.** |
| `ChatGPT-Agent Flow Optimization.md` | Parallelize independent repo inspection / testing / analysis. Scheduler must support fan-out. | **Use.** |
| `ChatGPT-LLM Architectures Discussion.md` | Confirms MoE economics: lower active params at inference for the same total quality. Validates the brief's "12B dense max, MoE preferred above" rule. | **Use.** |
| `ChatGPT-User-level Deterministic Cache.md` | Canonicalize user prompts (whitespace, ordering, formatting) to maximize prefix-cache hits. Aligns with vLLM/SGLang prefix cache designs. | **Use; pipe into `pheno/harness/prompt_canon.py` in next phase.** |

---

## 5. Gap analysis: brief vs current pheno-harness

| Brief ask | Status | Where it lands |
|---|---|---|
| Audit architecture / model-provider abstraction / tool loop / trace / eval hooks / concurrency / safe metrics | Partial. `pheno-harness` has the spine; needs a fresh audit doc with file:line citations. | This file (`RESEARCH_AUDIT.md`) + `EVAL_ARCHITECTURE.md`. |
| TB 2.0 via Harbor | Done in skeleton. Add TB 2.1 + TB 3.x watch. | `pheno-harness/config/harbor_tbench_models.yaml` |
| TB 3.0 compatibility watch | Missing. | Add `pheno-harness/config/harbor_tbench_v3.yaml` + watch script. |
| DeepSWE integration | Missing. | Add `pheno-harness/eval/deepswe.py` + `config/deepswe_models.yaml`. |
| SWE-bench Verified / Lite regression | Missing. | Add `pheno-harness/eval/swebench.py` + `config/swebench_models.yaml`. |
| Custom Harbor-compatible suites (coding / STEM / long-horizon / harness quality / verbosity / latency / cost / multi-agent roles) | TB2 covers some; role/verbosity/long-horizon/custom missing. | Add per-suite drivers under `pheno-harness/eval/`. |
| Trace-derived evalset across Claude / Codex / ForgeCode / Factory Droid / Cursor | Ingest exists (`traces/ingest.py`); per-role eval does not. | Add `pheno-harness/eval/trace_roles.py` + schema in `TRACE_EVALSET_PLAN.md`. |
| Single-agent latency / N-agent parallel throughput / TTFT / ITL / tokens/sec / CPU+RAM+VRAM+disk+net / leaks / deadlocks / queueing / cache hit / retry behavior / harness overhead | Largely missing. `wastage.py` is rough wastage analysis only. | Add `pheno-harness/perf/profiler.py` + `MODEL_MATRIX.md`. |
| Local model matrix 0.8B → 35B, dense vs MoE, engine matrix (vLLM/SGLang/TRT-LLM/llama.cpp/MLX), quantization options, 3090 Ti fitting strategy | Local matrix YAML exists for one tier (ik_llama); full engine matrix missing. | Add `pheno-harness/config/model_engine_matrix.yaml` + `MODEL_MATRIX.md`. |
| M1 Pro 16 GB fallback | Only `runtime: cpu` placeholder. No MLX. | Add `pheno-harness/config/m1_fallback.yaml` + MLX worker. |
| Intent-graph / scheduler architecture | Pheno is chat-loop. | New `pheno-harness/harness/intent_graph/` package; design in `EVAL_ARCHITECTURE.md`. |
| Self-improvement loop (garden-managed, not "just told to RLVRAF") | Partially wired (`nested_rlvr.py`, `nightly_dpo.py`, `train_sub1b.py`, `distill_12b.py`). Missing: signal/gate/retention policy; eval-clock; cross-lane promotion. | Fold into `IMPLEMENTATION_PLAN.md` §4. |

---

## 6. Unknowns to resolve before implementation

1. **Submodule state of `agileplus-specs/` inside pheno-harness.** AGENTS.md implies it's a submodule, but local dir was not confirmed. Decide: pin a commit hash or treat as content of `pheno-harness/specs/`?
2. **OpenRouter API key handling.** Brief says "use `OPENROUTER_API_KEY`, never print, store, or commit." Add a secrets-loader pattern and forbid `os.environ.get("OPENROUTER_API_KEY")` from being logged. (See `RISKS.md` §3.)
3. **GPU driver / CUDA / vLLM version on the 3090 Ti.** Need `nvidia-smi`, `nvcc --version`, `pip show vllm sglang triton` baseline before writing perf specs. Cannot skip.
4. **Disk pressure.** NVMe is "mostly full" per brief. All eval sandboxes + model weights + trace stores compete for space. Need a `state/disk_budget.yaml` and a GC policy.
5. **Codex fork local state.** Empty. Stage 2 is gated on user sign-off. Do not start.
6. **OmniRoute on the dev machine.** Config present (`combo_main.json`), runtime absent. Plan must accommodate both "OmniRoute available" and "OmniRoute unavailable → direct provider call" modes in `pheno/harbor_util.py`.

---

## 7. Self-improvement loop — what "garden-managed" actually means

The brief contrasts "just told to RLVRAF" with a managed self-improvement loop. The audit pins the requirements before `IMPLEMENTATION_PLAN.md` fills the implementation.

**Required signals (every loop tick must observe at least these):**
- **Per-task signal:** pass/fail, wall time, turns, tool calls, tokens in/out, cost, patch size, test pass rate, regressions, verbosity, escalation count, recoverability.
- **Per-lane signal:** same, aggregated per `harness/lanes.yaml` lane.
- **Per-route-kind signal:** same, aggregated per `omniroute_cloud | local_direct | omniroute_combo`.
- **Per-role signal:** same, aggregated per the trace-derived role taxonomy (planner, reviewer, QA, perf, integration, advisor).
- **Per-serving-engine signal:** TTFT, ITL p50/p95/p99, aggregate tokens/sec, queue wait, cache hit rate, harness overhead.

**Required gates (no promotion without all green):**
- **Holdout gate:** eval holdout must score ≥ X (X from `config/eval_pillars.yaml` thresholds, not from training set).
- **Regression gate:** SWE-bench Verified subset must not regress.
- **Safety gate:** `verifier/risky_action.py` must remain at 0 high-severity violations.
- **Budget gate:** `eval/budget.py` cost ≤ budget_targets ceiling.
- **Reproducibility gate:** every run logs commit hash, model id, provider, hardware profile, env vars.

**Required retention:**
- All trace records retained for the eval window + a rolling 30-day archive.
- Nightly DPO candidates filtered against the holdout BEFORE training (already partially done in `eval/tbench.py`).

**Required evaluator clocks:**
- **Real-time clock:** wall-clock budget per task (e.g. 5 min micro-eval from `config/local_model_bench_matrix.yaml`).
- **Eval clock:** full Harbor TB2/2.1 sweep on a weekly cadence.
- **Promotion clock:** lane promotion only after two consecutive green windows.

These become the spine of the new `pheno-harness/harness/self_improvement/` package proposed in `IMPLEMENTATION_PLAN.md` §4.

---

## 8. Citations index (for downstream docs)

- Harbor tutorial: <https://www.harborframework.com/docs/tutorials/running-terminal-bench>
- TB3 repo: <https://github.com/harbor-framework/terminal-bench-3>
- TB landing (2.x leaderboard + 2.1): <https://www.tbench.ai/>
- DeepSWE: <https://deepswe.datacurve.ai/> · <https://github.com/datacurve-ai/deep-swe>
- OpenRouter ling-2.6-flash: <https://openrouter.ai/inclusionai/ling-2.6-flash>
- vLLM prefix cache: <https://docs.vllm.ai/en/stable/design/prefix_caching/>
- vLLM speculative decoding: <https://docs.vllm.ai/en/latest/features/speculative_decoding/>
- SGLang: <https://docs.sglang.ai/>
- TensorRT-LLM: <https://nvidia.github.io/TensorRT-LLM/overview.html>

Local corpus (relative paths under `D:\koosh\Downloads\`) cited individually in `TRACE_EVALSET_PLAN.md` and `MODEL_MATRIX.md`.