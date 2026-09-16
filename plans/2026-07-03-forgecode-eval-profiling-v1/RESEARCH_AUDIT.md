# RESEARCH_AUDIT.md

Date: 2026-07-03
Owner: ForgeCode audit (this repo)
Status: v1 — research + audit only. No code changes yet.
Purpose: Establish the verified factual ground for the eval + profiling program
described in `IMPLEMENTATION_PLAN.md`.

This document is intentionally evidence-backed. Every claim that touches a
benchmark, a serving engine, a model, or a price has at least one primary
source. Unverified items are called out in **§7 Unknowns**.

---

## 1. Operating envelope (confirmed locally)

| Surface | Path | What it actually is |
|---|---|---|
| Global Forge home | `C:\Users\koosh\forge\` | Houses `AGENTS.md`, `.forge.toml`, Rust crates `forge-cli`, `forge-runner`, `governance-resolver`, `prompt-library`, `skill-manifest`. **Not** a `forgecode` source tree. |
| Eval + profiling surface | `C:\Users\koosh\pheno-harness\` | Real, structured scaffold. See §3. |
| Other user-named roots | `~/forge-dev`, `~/forgecode`, `~/codex-fork` | **Do not exist.** Either the brief used a working name that was never created, or it lives on remote only. |
| `~/pheno-specs` (claimed submodule of pheno-harness) | missing | The `AGENTS.md` describes `agileplus-specs` as the submodule; neither is currently initialized. |
| `~/codex-work` | empty dir | Nothing to integrate yet. |
| `~/omniroute-dev` | log dump | **Not** the live router. The actually-running router is whatever `combo_main.json` points at inside `pheno-harness/config/`. |
| M1 Pro laptop (secondary) | `M1 Pro 10c, 16 GB` | Confirmed only in the brief. No MLX/serving infra present locally. |
| Windows primary | `64 GB DDR4 / RTX 3090 Ti 24 GB / 2 TB NVMe (~95% full)` | Confirmed in brief. **2 TB ≈ full is the binding disk constraint** for any eval run. |
| OpenRouter API key | `OPENROUTER_API_KEY` (env) | Referenced in `config/cloud_tiers.yaml` and `config/combo_main.json`. Never committed. |

**Implication:** the entire program below is staged against `pheno-harness/`
because that's where the eval and benches already exist. There's no second
repo to start from — that's a brief-vs-reality correction we should make
explicit (see `RISKS.md` §3).

---

## 2. Primary-source verification (verified today)

| Claim | Source | Status |
|---|---|---|
| TB2.0 = 89 isolated tasks; official Harbor harness | `harborframework.com/docs/tutorials/running-terminal-bench` + `tbench.ai` | **Confirmed.** |
| TB2.1 = "improved version, inspired by Z.ai's TB2.0 Verified" | `tbench.ai/leaderboards/terminal-bench-2-1` | **Confirmed** (not yet mentioned in `eval/HARBOR.md`). |
| TB3.0 active dev at `harbor-framework/terminal-bench-3` | GitHub org | **Confirmed.** |
| TB2.0 verified-subset leaderboard top scores ~0.85 (Codex on GPT-5.5 = 0.822, Meta-Harness on Opus 4.6 = 0.764, Droid on GPT-5.3-Codex = 0.773) | `tbench.ai` leaderboard, July 2026 | **Confirmed.** |
| DeepSWE = 113 tasks (TS/Go/Python/JS/Rust), Harbor task format, separate-verifier since v1.1, requires Pier ≥ 0.3.0 | `github.com/datacurve-ai/deep-swe` README | **Confirmed.** |
| Artificial Analysis Coding Agent Index = composite of DeepSWE + Terminal-Bench v2 + SWE-Atlas-QnA | `artificialanalysis.ai/code-agents` | **Confirmed.** |
| `inclusionai/ling-2.6-flash` = 104B total / 7.4B active MoE, **262 K context**, $0.01 / 1M in, $0.03 / 1M out (90% off promo), released 2026-04-21, agent-oriented | `openrouter.ai/inclusionai/ling-2.6-flash` | **Confirmed.** |
| vLLM: prefix caching (block-allocation, LRU, hash-based matching, ops), speculative decoding (EAGLE / MTP / N-gram / Suffix / Speculators / MLP-draft / parallel-draft), LoRA, AWQ, BnB, FP8, GGUF, GPTQModel, ModelOpt, NVFP4 on Blackwell, KV offloading, OpenAI-compat, Codex integration, Claude Code integration, **profiling page** | `docs.vllm.ai/en/stable/design/prefix_caching/`, `features/speculative_decoding/`, `features/quantization/`, `serving/openai_compatible_server/`, `usage/profiling/` | **Confirmed.** |
| SGLang: low-latency/high-throughput, agent-optimized APIs | `docs.sglang.ai` | **Confirmed** at landing-page level (full feature grid still to sweep). |
| TensorRT-LLM: in-flight batching, paged KV, spec-dec, quant, multi-GPU | `nvidia.github.io/TensorRT-LLM/overview.html` | **Confirmed.** |
| OmniRoute exists upstream of pheno-harness and is referenced by `config/combo_main.json` | local configs | **Confirmed** as the router the brief asks about; **not** `~/omniroute-dev`. |

**Brief-vs-reality corrections worth flagging:**

1. Brief said OpenRouter ling-2.6-flash had "long context." It's 262 K — large
   but specific. Harness should still pin it explicitly per request (see
   `MODEL_MATRIX.md` §3).
2. Brief said the harness fork is "forgecode" or "forge-dev." Neither exists;
   the actual work surface is `pheno-harness/`. Plan adapts.
3. Brief's claim that vLLM/SGLang/TRT-LLM are "considerations"; locally only
   llama-server (ik_llama fork) is wired. **This is the widest gap** and
   drives most of `MODEL_MATRIX.md`.

---

## 3. Pheno-harness current state (concrete surfaces)

This is the working file-by-file audit so future sections don't drift.

### 3.1 Top-level (`C:\Users\koosh\pheno-harness\`)

```
pheno-harness/
├── AGENTS.md                  # North star: "verified steps / sec / GB / $"
├── README.md
├── specs.lock
├── agileplus-specs/           # submodule (not initialized locally)
├── bench/                     # CPU mat + micro-evals
├── config/                    # 20+ YAMLs (lanes, models, runners, pillars…)
├── eval/                      # TB2 leaderboard, route matrix, pillars, budget
├── harbor/                    # Harbor harness helpers
├── harness/                   # lanes.yaml (role routing)
├── pheno/                     # local swarm + paths + model manager
├── plans/                     # this document set
├── scripts/                   # ~30 driver scripts
├── training/                  # RLVR / distill / draft / eval_holdout configs
└── verifier/                  # harness.py + rewards.py + risky_action.py
```

### 3.2 `eval/` — what already exists

| File | Role | Reuse or build new? |
|---|---|---|
| `eval/tbench.py` | TB2 leaderboard via Harbor. `n_attempts=1`, holdout excluded from `nightly_dpo`. terminus-2 task set. | **Reuse as the TB2 baseline.** |
| `eval/route_matrix.py` | Composite `40% accuracy / 30% speed / 30% cost` over `omniroute_cloud \| local_direct \| omniroute_combo` route kinds. | **Reuse as the route-mode scorer.** Extend with `local_only` + `hybrid_n` for the new sweep. |
| `eval/pillars.py` + `config/eval_pillars.yaml` | 7-pillar scoring (acceptance, throughput, RAM, VRAM, $, stability, retries). | **Reuse.** |
| `eval/budget.py` + `config/budget_targets.yaml` | Per-run cost ledger. | **Reuse.** |
| `eval/nested_rlvr.py` | L0/L1/L2/L3 + soft-SVeRL + MR-RLVR. | **Reuse;** `_holds` and loss macros are the cleanest place to add per-role reward shaping. |
| `eval/HARBOR.md` | Local Harbor notes. | **Reuse; update for TB2.1 + 3.x paths.** |

### 3.3 `pheno/` — what already exists

| File | Role | Reuse or build new? |
|---|---|---|
| `pheno/model_manager.py` | Local swarm: ik_llama-server, always-on Qwen4B (`Qwen3-4B-Instruct-2507-Q4_K_M`) + `0.6B draft`, on-demand swap for larger MoE. | **Reuse;** extend with SGLang/vLLM/TRT-LLM adapters per `MODEL_MATRIX.md`. |
| `pheno/harbor_util.py` | Harbor + OmniRoute env wiring. | **Reuse;** add DeepSWE task pack loader. |
| `pheno/paths.py` | Repo-rooted path resolution. | **Reuse.** |
| `pheno/router.py` | (does not exist as a module file — routing lives in `config/combo_main.json` + `pheno/harbor_util.py`) | **Treat as JSON config**, not code. |

### 3.4 `verifier/`, `traces/`, `harness/`, `training/`

- `verifier/harness.py` — RLVR + risky-action gate (already wired; see §4).
- `verifier/rewards.py`, `verifier/risky_action.py` — same.
- `traces/ingest.py` — multi-source ingest (OmniRoute SQLite, forge history, codex, claude, cursor, factory droid). **This is the seed for `TRACE_EVALSET_PLAN.md`.**
- `traces/motion.py` + `traces/wastage.py` — coarse perf + cost telemetry.
- `harness/lanes.yaml` — five role lanes (`routine`, `ci`, `architecture`, `medium_hard`, `research`).
- `training/*.yaml` — RLVR (nested L0/L1/L2/L3), distill 12B, draft 0.6B, eval holdout, sub-1B needle.

### 3.5 `config/` — governance layer (already substantial)

| File | Purpose | Use in eval plan |
|---|---|---|
| `eval_pillars.yaml` | 7-pillar weights | Reuse as ground-truth for composite. |
| `inference_runners.yaml` | SGLang (primary) / vLLM (secondary) / llama-server (legacy) / BitNet (sub-1B); TRT-LLM = `not_recommended_primary` because of compile overhead | Reuse as the runner table; extend with MLX on M1 Pro. |
| `models.yaml` | cloud + local candidate lists | Reuse; extend with `local_35b_moe` tier. |
| `local_model_bench_matrix.yaml` | tier-by-tier inference intent | Reuse as scaffold for `MODEL_MATRIX.md`. |
| `decode_acceleration_matrix.yaml` | speculative-decoding / EAGLE / draft pairing per tier | Reuse. |
| `moe_deploy_policy.yaml` | MoE economics / swap policy | Reuse; gates serve decisions. |
| `risky_action_gate.yaml` | denies risky ops (rm, chmod 777, force-push, etc.) | Reuse. |
| `activation_edit_policy.yaml` | activation-edit / SP hygiene | Reuse. |
| `context_caps.yaml` | per-tier context caps | Reuse; pin ling-2.6-flash at 262 K. |
| `budget_targets.yaml` | $/run ceilings | Reuse. |
| `role_lora.yaml` | per-role LoRA loads | Reuse. |
| `cloud_tiers.yaml` | cloud routing tiers | Reuse. |
| `combo_main.json` | Main OmniRoute blend | Reuse. |
| `local_swarm.yaml` | ik_llama-server fleet | Reuse. |
| `harbor.yaml`, `harbor_tbench_models.yaml`, `harbor_tbench_routes.yaml`, `harbor_tbench_agent.yaml` | Harbor wiring | Reuse; extend with deepswe pack + swa-bench Verified. |
| `playground_matrix.yaml`, `repo2rl.yaml`, `kv_bakeoff.yaml` | micro-eval harnesses | Reuse for `bench/`. |

### 3.6 `scripts/` — driver surface

The 30+ scripts already cover:
- `run_tbench_route_matrix.py`, `run_tbench_model_matrix.py`, `run_eval_suite.py`, `run_playground.py`
- `tbench_scoreboard.py`, `tbench_route_scoreboard.py`
- `collect_traces.py`, `analyze_wastage.py`
- `repo2rl_setup.py`, `repo2rl_eval.py`
- `kv_bakeoff.py`, `decode_prepare.py`, `moe_prepare.py`, `activation_prepare.py`
- `nightly_dpo.py`, `train_sub1b.py`, `distill_12b.py`
- `probe_omniroute_models.py`, `probe_tbench_routes.py`
- `compile_context.py`, `start_local_swarm.ps1`

These are the operations surface to keep working; the eval/profiling program
extends them, not rewrites them.

---

## 4. Verifier + risk-gate layer

`verifier/harness.py` couples `verifier/rewards.py` (multi-signal RLVR) with
`verifier/risky_action.py` (denies denylist ops before they execute). This is
already close to what the brief asks for under "harness quality" — the
extension is to wire it into *every* eval trace, not just DPO candidates, and
to count denials as a first-class metric (see `RISKS.md` §6).

`config/risky_action_gate.yaml` already lists the usual suspects (rm, chmod,
force-push, sudo, caddy reload, etc.). Reuse.

---

## 5. Local corpus (D:\koosh\Downloads\ChatGPT-*.md)

The brief points at 16 specific ChatGPT files. They've been skim-read for
alignment with the eval / profiling plan; nothing here *contradicts* primary
sources, but several materially shape `MODEL_MATRIX.md` and
`TRACE_EVALSET_PLAN.md`. Highlights only:

| File | Salient fact used by plan |
|---|---|
| `ChatGPT-Coding Agents and Intent Graphs (1).md` | Planner DAG > chat loop — see `IMPLEMENTATION_PLAN.md` §6. |
| `ChatGPT-Agent-Aware Speculative Decoding.md` | Context-aware draft selection; reuses prefix-cache hash. |
| `ChatGPT-RLVR-AF Optimization Proposal (1).md` | Acceptance-feedback reward (was the v0 RLVRAF seed). Plan now treats AF as one signal among many (see self-improvement loop). |
| `ChatGPT-VRAM and Scaling Factors (1).md` + `…RTX 3090 Throughput Analysis.md` | 24 GB 3090 Ti fits Qwen4B + 0.6B draft comfortably; 12B dense borderline; MoE 27B+ needs aggressive quant + swap. Drives `MODEL_MATRIX.md` §5. |
| `ChatGPT-LatentMAS vs TextMAS comparison (1).md` | Multi-agent options: latent-MAS vs text-MAS. Latent is cheaper; text wins on explainability. Both tracked as configs. |
| `ChatGPT-User-level Deterministic Cache.md` | KV-cache reuse + canonicalized prompt for repeated bench loops; reduces variance and cost. |
| `ChatGPT-Model improvements under $500.md` | Hard price band for consumer-model upgrades; relevant to `MODEL_MATRIX.md` pricing col. |
| `ChatGPT-Machine Comparison for AI.md` | Codifies 3090 Ti / M1 Pro / Blackwell tradeoffs. |
| `ChatGPT-Model Inference Costs 2026.md` | Spot-check vs OpenRouter API. |
| `ChatGPT-Efficiency Evolutions Post-MoE (1).md` | MoE economics are non-linear; large-active-fraction MoE hurts on 24 GB. |
| `ChatGPT-Compression Pruning Review (2).md` | AWQ/GPTQ/FP8/ablation sparsity ladder. |
| `ChatGPT-AI Inference Hardware Costs (1).md` | Coarse TCO. |
| `ChatGPT-Concurrent Lint Command Handling.md` | Subprocess-fanout patterns for parallel lint/test. |
| `ChatGPT-Agent Flow Optimization.md` | Per-agent pacing, queue sizing. |
| `ChatGPT-LLM Architectures Discussion.md` | Background taxonomy. |
| `ChatGPT-Feature graph system design.md` | Same idea as intent-graph for planner. |

---

## 6. Conventions observed across the repo (so plan reads native)

- YAML for governance; JSON (`config/combo_main.json`) only where dynamic.
- Scripts are PS1 + Python; both `~/forge/crates/*` (Rust) and `pheno-harness`
  Python coexist via `pheno.paths`.
- Self-improvement loop (RLVR / nightly DPO / 12B distill / 0.6B draft) is
  *already wired* through `verifier/` + `training/` + `scripts/`. The new
  program's job is to feed it better signals, not redo it.
- Currency convention: composite scores `40 acc / 30 spd / 30 cost`. Reused
  without change.
- Trace ingest is presumed sqlite-or-jsonl; no DB migrations implied.

---

## 7. Unknowns / to verify before execution

1. **DeepSWE Pier version pinning.** `datacurve-ai/deep-swe` README requires
   Pier ≥ 0.3.0, but the *exact* `pier` CLI flag surface changes per minor.
   Verify on the doc site before drafting PR #1's DeepSWE adapter.
2. **TB2.1 task list.** The live site says "inspired by TB2.0 Verified"; we
   don't have a canonical task-id set yet. Decide whether the eval plans runs
   *both* `terminal-bench@2.0` and `@2.1`, or replaces.
3. **SGLang vs vLLM agent-suitability on Windows.** Pheno declares SGLang
   primary; we should verify it actually loads `Qwen3-4B-Instruct-2507`
   + ik draft, with `--tool-call-parser` stable, before PR #3's
   `pheno/model_manager.py` extension is merged.
4. **MLX on M1 Pro.** No MLX install evidence locally. Confirm pip/pkg
   availability for the secondary-Mac target.
5. **BitNet sub-1B coverage on RTX.** Inference paths assume CUDA SM 8.6
   (3090 Ti). Verify kernel selection before PR #4.
6. **TB3.0 task-format breakage.** Once TB3 lands, task pack schemas change.
   Don't pin task schema in YAML; keep it behind a `harbor_packs/` loader.
7. **DISK pressure.** 2 TB at ~95% full means *every* run must clean its
   workspace before next, and `bench/results/` and `eval/results/` must be
   age-pruned. See `RISKS.md` §2.
8. **OmniRoute upstream version.** `combo_main.json` references `Main`; we
   don't have the upstream commit SHA pinned in this checkout. Lock it
   before claiming reproducible runs.

---

## 8. Bottom line

Pheno-harness already does roughly **70%** of what the brief is asking for.
What is genuinely missing:

1. **DeepSWE adapter** (task pack + Pier driver + verifier split).
2. **SWE-bench Verified / Lite regression runner.**
3. **Long-horizon + per-role evalset** (TB2 only; per-role only as `lanes`).
4. **Real perf profiler** (TTFT, ITL, tokens/s, ctx-cache, queue, harness
   overhead, N-agent scaling).
5. **Engine coverage** (vLLM, SGLang, TRT-LLM, llama.cpp, MLX — only llama-
   server is wired today).
6. **Intent-graph / scheduler refactor** (chat-loop → planner DAG).
7. **Self-improvement loop as a true garden** — today it's a pipeline of
   scripts; plan turns it into gates, retention, evaluator clocks, and
   authorship audit (see `IMPLEMENTATION_PLAN.md` §6 + `EVAL_ARCHITECTURE.md`
   §5).

The remaining sections of this plan set cover each gap with concrete PRs.
