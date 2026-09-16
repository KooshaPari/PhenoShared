# EVAL_ARCHITECTURE.md

> **Status:** Design for 2026-07-04 onward. Builds on `pheno-harness/` skeleton documented in `RESEARCH_AUDIT.md`.
> **Naming convention:** forks we own use the `-dev` suffix in their bin/path names — `forge-dev`, `omniroute-dev`, `pheno-serve-dev`, `codex-dev`. CI scripts, runbooks, and config keys refer to the forked binaries by these exact names so they never collide with upstream-installed binaries on `$PATH`. Canonical: `docs/ARCHITECTURE_LAYERS.md`.
> **Locked model baseline:** 8 OpenRouter cloud baselines + 3 self-hosted aliases (`local/qwen35-08b`, `local/lfm25-8b-a1b`, `local/ornith-8b`). See `state/hf_scrape/2026-07-04/locked_shortlist.md` + ADR 0005.
> **Cost projection:** `state/hf_scrape/2026-07-04/cost_projection.md` covers per-run $ across the matrix.

---

## 0. Goals (what this architecture must answer)

1. **Semantic agent eval:** how well does a single agent (or a multi-agent team) complete a well-written task — accuracy, robustness, recoverability?
2. **Harness eval:** is the harness itself helping or hurting? Verbosity, latency overhead, deadlocks, retry storms, context pollution.
3. **Serving eval:** literal compute performance — TTFT, ITL, tokens/sec, queue depth, cache hit rate, VRAM/RAM/disk pressure, harness overhead independent of model latency.
4. **Composition:** every benchmark run is reproducible from `(commit hash, model id, provider, route kind, engine, quantization, hardware profile, env vars)`.
5. **Layering:** model quality, harness quality, and serving performance are scored independently and can be multiplied for a composite. Never collapse them.

---

## 1. Repository layout (proposed additions)

All paths relative to `pheno-harness/`. Existing files are not renamed.

```
pheno-harness/
├── audit/                          # this deliverable + siblings
├── eval/
│   ├── tbench.py                   # existing — TB 2.0 driver
│   ├── tbench_v21.py               # NEW — TB 2.1 driver (terminal-bench@2.1)
│   ├── tbench_v3_watch.py          # NEW — TB 3.x compat smoke (gated, opt-in)
│   ├── deepswe.py                  # NEW — DeepSWE driver (113 tasks)
│   ├── swebench_verified.py        # NEW — SWE-bench Verified regression subset
│   ├── swebench_lite.py            # NEW — SWE-bench Lite regression subset
│   ├── long_horizon.py             # NEW — custom multi-day trace replay
│   ├── verbosity.py                # NEW — verbosity / cost-per-task leaderboard
│   ├── role_suite.py               # NEW — per-role trace eval (see TRACE_EVALSET_PLAN.md)
│   ├── route_matrix.py             # existing — composite (40/30/30)
│   ├── pillars.py                  # existing
│   ├── budget.py                   # existing
│   └── nested_rlvr.py              # existing
├── perf/
│   ├── profiler.py                 # NEW — hardware-level profiler (psutil + pynvml + GPUtil + custom IPC)
│   ├── ttft_probe.py               # NEW — TTFT/ITL p50/p95/p99
│   ├── cache_probe.py              # NEW — prefix-cache hit rate
│   ├── harness_overhead.py         # NEW — harness-only wall time vs. model wall time
│   ├── parallel_sweep.py           # NEW — N-agent fan-out sweeps
│   └── report.py                   # NEW — roll-up report → perf/results/
├── harness/
│   ├── lanes.yaml                  # existing
│   ├── intent_graph/               # NEW — planner DAG + scheduler
│   │   ├── planner.py
│   │   ├── dag.py
│   │   ├── tools.py                # deterministic tool registry
│   │   ├── scheduler.py
│   │   ├── recorder.py             # trace recorder (per node, per edge)
│   │   └── replay.py
│   └── self_improvement/           # NEW — garden-managed loop
│       ├── signals.py
│       ├── gates.py
│       ├── retention.py
│       └── promotion.py
├── config/
│   ├── harbor_tbench_models.yaml       # existing — extend with TB 2.1 + 3.x names
│   ├── harbor_tbench_routes.yaml       # existing
│   ├── deepswe_models.yaml             # NEW
│   ├── swebench_models.yaml            # NEW
│   ├── model_engine_matrix.yaml        # NEW — full engine matrix
│   ├── role_eval_models.yaml           # NEW
│   ├── m1_fallback.yaml                # NEW — MLX worker config
│   └── disk_budget.yaml                # NEW
├── scripts/
│   ├── ...                          # existing
│   ├── run_tbench_v21.py            # NEW
│   ├── run_deepswe.py               # NEW
│   ├── run_swebench_regression.py    # NEW
│   ├── run_perf_suite.py            # NEW — orchestrates perf/* probes
│   ├── run_intent_graph_smoke.py    # NEW
│   └── run_role_eval.py             # NEW
└── bench/
    ├── fixtures/
    │   └── trace_replay/            # NEW — replayable task specs from real traces
    └── results/
        ├── tbench/                  # existing
        ├── deepswe/                 # NEW
        ├── swebench/                # NEW
        ├── role_eval/               # NEW
        └── perf/                    # NEW
```

---

## 2. Suite taxonomy

### 2.1 Semantic agent eval suites

| Suite | Driver | Source | Cadence | Metric primary |
|---|---|---|---|---|
| `tbench_20` | `eval/tbench.py` | Harbor TB 2.0 (89 tasks) | weekly | accuracy | **PRIMARY** |
| `tbench_21` | `eval/tbench_v21.py` | Harbor TB 2.1 (improved subset, post-2026-06) | weekly | accuracy | **PRIMARY** |
| `tbench_3_watch` | `eval/tbench_v3_watch.py` | TB 3.x smoke | opt-in monthly | compat | watch-only |
| `deepswe` | `eval/deepswe.py` | datacurve-ai/deep-swe (113 tasks, TS/Go/Python/JS/Rust) | weekly | accuracy + wall time | **PRIMARY** (long-horizon SWE) |
| `long_horizon` | `eval/long_horizon.py` | Harbor-compatible multi-day task replays from real traces (see `TRACE_EVALSET_PLAN.md`) | monthly | accuracy + recoverability | **PRIMARY** (custom long-horizon) |
| `swebench_verified` | `eval/swebench_verified.py` | SWE-bench Verified subset (200) | **deprioritized** | pass@1 + regression | smoke-only / regression-anchor |
| `swebench_lite` | `eval/swebench_lite.py` | SWE-bench Lite (300) | dropped | pass@1 | dropped per user preference |
| `long_horizon` | `eval/long_horizon.py` | Replayable task specs derived from real traces (see `TRACE_EVALSET_PLAN.md`) | monthly | accuracy + recoverability |
| `role_solo_engineer` | `eval/role_suite.py` | Trace-derived | weekly | role-specific composite |
| `role_coding_subagent` | same | same | weekly | same |
| `role_reviewer` | same | same | weekly | same |
| `role_planner` | same | same | weekly | same |
| `role_qa` | same | same | weekly | same |
| `role_perf` | same | same | weekly | same |
| `role_integration` | same | same | weekly | same |
| `role_advisor` | same | same | weekly | same |
| `verbosity` | `eval/verbosity.py` | Cross-suite roll-up | nightly | tokens/task, cost/task, lines/text |

### 2.2 Performance / serving eval suites

| Suite | Driver | What it measures | Cadence |
|---|---|---|---|
| `perf_single` | `perf/ttft_probe.py` + `cache_probe.py` | TTFT, ITL, tokens/sec at concurrency 1 | per-deploy |
| `perf_parallel` | `perf/parallel_sweep.py` | N-agent fan-out for N ∈ {1, 2, 4, 8, 16} on the local 3090 Ti | per-deploy |
| `perf_cache` | `perf/cache_probe.py` | prefix-cache hit rate across canonical vs. raw prompts | per-deploy |
| `perf_harness_overhead` | `perf/harness_overhead.py` | harness wall time vs. model wall time at fixed load | weekly |
| `perf_resource` | `perf/profiler.py` | CPU/RAM/VRAM/disk/net + queue depth + deadlocks + leaks | per-deploy |
| `perf_resilience` | `perf/profiler.py` (resilience mode) | crash rate, retry storms, deadlock recovery | weekly |

All perf suites tag every run with `(commit, model_id, route_kind, engine, quantization, hw_profile, env)` and write to `bench/results/perf/<date>_<suite>_<tag>.json` plus a roll-up `perf/latest.json`.

---

## 3. The four waypoints (early program)

### Waypoint 1 — TB 2.0 honest baseline

- Reproduce pheno-harness's existing `tbench.py` run on the verified TB 2.0 subset.
- Publish numbers into `bench/results/tbench/` and tag as `tbench_20_baseline_<date>`.
- Confirm terminus-2 agent baseline + provider latency.

### Waypoint 2 — TB 2.1 lift

- Add `eval/tbench_v21.py` (driver skeleton mirrors `tbench.py`).
- Update `config/harbor_tbench_models.yaml` to include `terminal-bench@2.1` task list.
- Re-run nightly. Compare to TB 2.0 numbers; expect noise of ±3 %, not structural drift.

### Waypoint 3 — DeepSWE integration

- Implement `eval/deepswe.py` with separate verifier (per DeepSWE v1.1 spec).
- Use Pier ≥ 0.3.0; configure `--env modal` for parallel sandboxes when on cloud route.
- Run on a small subset first (16 tasks) before the full 113.

### Waypoint 4 — SWE-bench Verified regression
### Waypoint 4 — SWE-bench Verified (deprioritized)
- `eval/swebench_verified.py` exists for **regression-anchor only** (not a primary ranking signal). Once the cross-task composite is trustworthy, drop nightly runs to weekly, then monthly.
- Frozen 200-task subset, held out from training by `training/eval_holdout.yaml`.
- Any drop > threshold fails the regression gate in `harness/self_improvement/gates.py`. Track but never optimize against.

### Waypoint 5 — Long-horizon custom Harbor-compatible
- `eval/long_horizon.py` runs replayable multi-day spec derived from real agent traces (see `TRACE_EVALSET_PLAN.md` for the spec schema).
- Sourced from Claude / Codex / ForgeCode / Factory Droid / Cursor-agent / public long-orchestration chats.
- Per-role scored separately. Includes recoverability, escalation, and tokenizer-rotation metrics.
---

## 4. Intent-graph / scheduler architecture (the next big build)

Today `pheno-harness` runs as a chat-loop harness: agent turn → tool call → next turn. The brief and the corpus both call for an intent-graph layer.

### 4.1 Why

- **Latency:** deterministic tools (grep, ripgrep, AST search, test runners, lint, build, type-check) can run **without** a model call. Today every `cat` and `pytest` round-trips through the model.
- **Cost:** same.
- **Recoverability:** typed DAG lets us retry just the failed node instead of replaying the whole chat.
- **Replayability:** traces become executable graphs — we can replay any historical attempt with a different model, engine, or quantization and get apples-to-apples metrics.
- **Multi-agent:** planner + sub-agents map onto the DAG; sub-agents are weak/local workers on leaf tasks.

### 4.2 Schema (typed DAG)

```yaml
# Conceptual; not committed yet. Goes into harness/intent_graph/dag.py
node:
  id: string
  kind: plan | search | read | edit | test | build | review | merge | advise
  inputs: { [k: string]: NodeRef | Literal }
  pre: [Predicate]              # gates that must be true to start
  post: [Predicate]             # assertions that must hold on completion
  budget: { wall_s: int, tokens: int, cost_usd: float }
  agent: { lane: string, role: string, model_ref?: string }
edge:
  from: NodeRef
  to: NodeRef
  when: Predicate
```

### 4.3 Executor model

- **Planner** runs on the strongest available model (`medium_hard` or `architecture` lane). Produces DAG.
- **Deterministic tool executor** runs search/read/edit/test/build nodes without any LLM call. Uses `ripgrep`, `ast-grep`, `pytest`, `cargo`, `tsc`, etc.
- **Weak/local workers** (Qwen 4B, 0.6B draft) handle leaf tasks like formatting, docstring polish, simple renames.
- **Strong re-entry** on failure: only when `post` predicates fail does the strong model re-enter (review / merge / advise).
- **Scheduler** parallelizes independent branches using `asyncio.TaskGroup` (or `trio`) and reports queue depth to `perf/profiler.py`.

### 4.4 Trace recorder

- Every node emits `(node_id, started_at, ended_at, model_calls, tool_calls, tokens, cost, post_result, retries)`.
- Every edge emits `(from_node, to_node, when_predicate_result, latency_ms)`.
- Records roll up to `bench/results/<suite>/<run_id>.trace.jsonl` and a sibling `.graph.json`.
- Replay loads `.graph.json` + a model binding override and re-executes deterministically.

### 4.5 Migration strategy

The chat-loop must keep working while the intent-graph layer comes online. Stages:

1. **Stage A — passive recording.** Add a recorder that observes the chat loop and emits `.graph.json` after each run. No DAG planning yet. No behavior change. (See `IMPLEMENTATION_PLAN.md` §2.)
2. **Stage B — deterministic tool injection.** Wrap `read`, `search`, `test`, `build` calls into a `tools.py` registry and execute them without LLM. Reduces cost by ~20–40 %.
3. **Stage C — DAG planning.** Add `planner.py`. Start with a "single-shot plan" mode: planner emits a DAG, executor runs it once. Fall back to chat loop on planner failure.
4. **Stage D — multi-agent fan-out.** Sub-agents become typed nodes. `scheduler.py` parallelizes.
5. **Stage E — strong re-entry.** Add review/merge nodes with holdout-aware promotion.

---

## 5. Metric taxonomy

### 5.1 Semantic metrics (per task)

| Metric | Definition | Source |
|---|---|---|
| `pass` | Boolean | verifier |
| `wall_s` | End-to-end wall time | profiler |
| `turns` | Number of model turns | recorder |
| `tool_calls` | Total tool invocations | recorder |
| `tokens_in` / `tokens_out` | Token totals | provider + recorder |
| `cost_usd` | Dollars spent | `eval/budget.py` |
| `patch_loc` | Lines changed in final patch | `git diff` |
| `test_pass_rate` | Tests passing / tests run | verifier |
| `regressions` | New failing tests not in baseline | verifier |
| `verbosity_tokens_per_loc` | tokens / patch_loc | derived |
| `escalations` | Times the harness re-entered strong model | recorder |
| `recoverable` | Boolean: succeeded within budget after ≥ 1 failure | recorder |

### 5.2 Harness metrics (per run)

| Metric | Definition | Source |
|---|---|---|
| `harness_overhead_ms` | harness wall time − model wall time | `perf/harness_overhead.py` |
| `deadlocks` | count | `perf/profiler.py` |
| `leaks` | count (file descriptors, child processes) | `perf/profiler.py` |
| `crash_count` | count | `perf/profiler.py` |
| `retry_storm_count` | count (retries > threshold in window) | `perf/profiler.py` |
| `context_cache_hit_rate` | hits / total | `perf/cache_probe.py` |

### 5.3 Serving metrics (per request, per engine)

| Metric | Definition | Source |
|---|---|---|
| `ttft_ms` | time to first token | engine |
| `itl_ms_p50/p95/p99` | inter-token latency | engine |
| `tokens_per_sec` | aggregate | engine + recorder |
| `queue_wait_ms` | time before engine accepted the request | `perf/profiler.py` |
| `vram_peak_gb` | peak VRAM | `pynvml` |
| `ram_peak_gb` | peak RAM | `psutil` |
| `cpu_pct` | CPU utilization | `psutil` |
| `disk_io_mb` | I/O during run | `psutil` |
| `net_io_mb` | network during run | `psutil` |

### 5.4 Composite scoring

`composite = w_pass · pass + w_speed · normalized_speed + w_cost · normalized_cost_inv`

Default `w_pass = 0.4, w_speed = 0.3, w_cost = 0.3` (already in `eval/route_matrix.py`). Pillar weights live in `config/eval_pillars.yaml`. Tunable per lane.

**Three axes are tracked separately and never merged:**
- `quality_axis = pass + robustness + safety`
- `harness_axis = verbosity + overhead + recoverability + determinism`
- `serving_axis = tokens_per_sec + cache_hit + ttft_p95 + vram_efficiency`

Composite is for ranking. Decomposition is for debugging.

---

## 6. Reproducibility contract

Every eval run writes a sidecar manifest:

```yaml
run_id: tbench_20_2026-07-03T14-22-31Z
suite: tbench_20
commit_sha: <git rev-parse HEAD>
model_id: inclusionai/ling-2.6-flash
provider: openrouter
route_kind: omniroute_cloud
engine: <vllm|sglang|trtllm|llama-server|mlx|ik_llama>
quantization: <awq|gptq|gguf|fp8|int8|none>
hardware:
  gpu: RTX 3090 Ti 24 GB
  cpu: <model>
  ram_gb: 64
  disk_free_gb: <at start of run>
env:
  OPENROUTER_API_KEY: <redacted>
  PHENO_HARNESS_PROFILE: <lane>
seeds:
  python: <random.seed()>
  numpy: <np.random.seed()>
held_out_from_training: true
holdout_hash: <sha256 of eval_holdout.yaml at run time>
artifacts:
  - bench/results/tbench/<run_id>.json
  - bench/results/tbench/<run_id>.trace.jsonl
  - bench/results/tbench/<run_id>.graph.json
```

No run without this manifest is accepted by the scoreboard.

---

## 7. Self-improvement loop (folded in; full spec in `IMPLEMENTATION_PLAN.md` §4)

Pheno-harness already has `verifier/`, `nested_rlvr.py`, `nightly_dpo.py`, `train_sub1b.py`, `distill_12b.py`. What's missing is the **gate logic** that decides what gets promoted and where.

The loop has four components:

1. **Signals** — emit per-task, per-lane, per-route-kind, per-role, per-engine (see §5).
2. **Gates** — holdout gate, regression gate, safety gate, budget gate, reproducibility gate.
3. **Retention** — 30-day rolling archive of `.trace.jsonl` + `.graph.json`.
4. **Promotion** — lane promotion only after two consecutive green windows on the eval clock.

`harness/self_improvement/` ships these as small modules so each gate is independently testable.

---

## 8. Subagent-driven build plan (parallelism)

Use the `task` tool to dispatch parallel subagents only where work is genuinely independent. Sequential gates stay in the main thread.

| Phase | Parallelizable? | Reason |
|---|---|---|
| Audit + plan (now) | No | single-agent writing; depends on pheno-harness internal reads |
| Waypoint 1 (TB 2.0 baseline) | No | single CLI run, single result |
| Waypoint 2 (TB 2.1 lift) | No | depends on Waypoint 1 |
| Waypoint 3 (DeepSWE) | Partially | suite setup can run in parallel with Waypoint 2; the run itself is serial |
| Waypoint 4 (SWE-bench Verified) | Yes | independent of DeepSWE; can run as its own parallel subagent |
| Intent-graph Stage A (passive recording) | No | touches core harness |
| Intent-graph Stage B (deterministic tools) | Partially | can split per-tool |
| Perf suite build (`perf/*`) | Yes | each probe is independent |
| Self-improvement loop build | Yes | signals / gates / retention / promotion are independent modules |

Subagents always report back to the main thread with file paths and a 5-line summary. The main thread composes the scoreboard.

---

## 9. Open architectural decisions (parking lot)
## 9. Open architectural decisions (parking lot)
1. **Latent-MAS vs text-MAS.** Corpus notes latent is cheaper but less inspectable. Decision deferred; do not commit.
2. **Planner-as-LoRA vs full-model planner.** Pheno-harness's `config/role_lora.yaml` already supports role-LoRA. Planner likely becomes a role-LoRA on the main lane model. Decide after Waypoint 2.
3. **Local vs cloud fan-out.** 3090 Ti runs the 3 self-hosted aliases (`local/qwen35-08b`, `local/lfm25-8b-a1b`, `local/ornith-8b`); cloud runs the 8 OpenRouter baselines via `forge-dev → omniroute-dev → OpenRouter`. Decide per-task kind.
4. **TB 3.x adoption cadence.** Watch monthly; adopt when Pier + Harbor TB3 combo passes a 50-task smoke.
5. **`combo_main.json` is held over from the pre-drop baseline.** The 10→7 cloud reduction needs the combo file regenerated; OR-side mix-blend rates may shift. Re-run `probe_omniroute_models.py` + `tbench_route_probe` after the first Stage-1 TB 2.0 run lands.
6. **DeepSWE per-language split?** 113 tasks are TS/Go/Python/JS/Rust. We have a Python-heavy local stack. Decide whether to weight per-language or aggregate flat. (Defer until first DeepSWE run.)
7. **Harbor Piers/Pier version coupling.** Both TB 2.1 and DeepSWE need Pier ≥ 0.3.0; if Harbor TB3 ships incompatible Pier, the watch-suite and the primary suites diverge on the env. Track per-release.
These are tracked, not blockers.