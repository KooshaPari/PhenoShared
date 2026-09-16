# EVAL_ARCHITECTURE.md

Date: 2026-07-03
Companion to: `RESEARCH_AUDIT.md`, `MODEL_MATRIX.md`,
`TRACE_EVALSET_PLAN.md`, `IMPLEMENTATION_PLAN.md`, `RISKS.md`.

This document describes what the eval + profiling program **does**, what
**plumbing** it adds, and how it stays separate from the harness core
(per `IMPLEMENTATION_PLAN.md` §1 — instrumentation only, no core rewrite
until gates pass).

---

## 1. Goals (and non-goals)

### 1.1 Goals

1. **Score agents** at three orthogonal planes so we never conflate them:
   - **Semantic agent quality** — does the task succeed?
   - **Harness quality** — is the *harness's* contribution to the loop
     beneficial, neutral, or harmful?
   - **Raw serving performance** — TTFT, ITL, tokens/s, GPU/CPU/RAM/VRAM,
     queue depth, ctx-cache hit rate, retries.
2. **Cover coding, terminal/STEM, and long-horizon tasks.**
3. **Separate single-agent from multi-agent runs** (`lanes`, not just prompts).
4. **Stay reproducible.** Every run carries `config_hash + commit_sha + model
   id + provider + runner + profile + env`. No exceptions.
5. **Stay cheap.** Default caps per `config/budget_targets.yaml`; over budget
   → automatic `bench/results/age_prune` + abort, not silent run-on.
6. **Feed the existing self-improvement loop** with rich signals — not just
   pass/fail.

### 1.2 Non-goals

- We're not building a new benchmark. We score on **existing** suites.
- We're not rewriting the chat loop in PR #1. We **instrument** first,
  **study** second, **edit chat-loop behavior only** when evidence supports
  it (gate-driven — see `IMPLEMENTATION_PLAN.md` §6).
- We are not auto-deploying new models to prod. Model swaps go through the
  `pheno/model_manager.py` governance layer, not direct edits.

---

## 2. Suite taxonomy

```
eval/suites/
├── tbench_2_0/                  # already exists (eval/tbench.py)
├── tbench_2_1/                  # NEW — same harness, terminal-bench@2.1
├── deepswe/                     # NEW — DeepSWE pack via Pier ≥0.3.0
├── swe_bench_verified/          # NEW — regression baseline
├── swe_bench_lite/              # NEW — fast smoke regression
├── long_horizon/                # NEW — custom Harbor-compatible tasks
│   ├── cross_repo_refactor/
│   ├── compiler_migration/
│   ├── eval_pipeline_construction/
│   └── multi_service_patch/
├── harness_quality/             # NEW — does the harness help or hurt?
│   ├── chat_loop_baseline/
│   ├── intent_graph_v1/
│   ├── deterministic_tool_only/
│   └── rerank_only/
├── verbosity/                   # NEW — token-per-success at fixed budget
│   ├── verbose_model_A/
│   ├── terse_model_B/
│   └── pass@k_recovery/
├── role_perf/                   # NEW — derived from lanes + per-role eval
│   ├── solo_engineer/
│   ├── coding_subagent/
│   ├── reviewer/
│   ├── planner_manager/
│   ├── qa_test_agent/
│   ├── perf_profiler_agent/
│   ├── release_integration_agent/
│   └── advisor_sponsor/
└── perf_profile/                # NEW — perf-only suite (see §6)
    ├── single_agent_latency/
    ├── n_agent_parallel_throughput/
    ├── ctx_cache_reuse/
    ├── queue_and_retry/
    └── harness_overhead/
```

Two structural rules:

1. **Every suite emits one `eval/results/<suite>_<ts>.json`** with the same
   envelope (`config_hash`, `commit_sha`, `model_id`, `provider`, `runner`,
   `hardware_profile`, `env_vars`, `started_at`, `ended_at`, `metrics`,
   `artifacts`).
2. Every suite declares a **cheapest-first 5-min micro-eval** that mirrors
   the protocol already wired in `config/playground_matrix.yaml`.

---

## 3. Score = three planes, one composite

### 3.1 Semantic agent quality (`score_agent_quality`)

Per-suit metrics:

| Metric | Source | Notes |
|---|---|---|
| `pass@1` (default) | verifier (TB-style) | `n_attempts=1` per `eval/tbench.py`. |
| `pass@3` | reducer | only when `n_attempts>1` (long-horizon). |
| `test_pass_rate` | verifier | patch-side; not behavioral. |
| `patch_size` | git diff | log-scale band, not score. |
| `regression_count` | verifier | tests that flipped green→red. |
| `recovery_turns` | trace | turns until next success after fail. |
| `escalations` | trace | agent requested stronger model. |
| `loop_invalid_repeat` | trace | detected cycles (`traces/motion.py`). |

### 3.2 Harness quality (`score_harness_quality`)

Differential metrics — always paired runs (intent-graph on vs. off):

| Metric | Description |
|---|---|
| `acceptance_delta` | pass@1 with intent-graph − pass@1 chat-loop. |
| `steps_per_success` | median steps to green. Lower = better. |
| `context_bloat` | tokens accumulated per task at end of run. |
| `replay_reproducibility` | % of runs that, when replayed with same config hash + same model id, match within ±5%. |
| `denied_action_rate` | how many risky actions were denied before harm. From `verifier/risky_action.py`. |
| `orphan_tool_calls` | tool calls not in the intent-graph's expected frontier. |

### 3.3 Raw serving performance (`score_serving`)

| Metric | How |
|---|---|
| `ttft_p50/p95` | first token from request send → first model token. |
| `itl_p50/p95` | inter-token latency, ignoring first. |
| `tokens_per_s` | total out-tokens / wall time per request. |
| `aggregate_tokens_per_s` | sum across concurrent workers. |
| `gpu_util`, `vram_peak`, `cpu_util`, `ram_peak`, `disk_io_mb`, `net_io_mb` | periodic sampler (1 Hz) from `psutil` + `pynvml`. |
| `ctx_cache_hit_rate` | from runner logs (vLLM `prefix caching`; SGLang `radix cache`; ik_llama `kv cache`; TRT-LLM `KV cache` stats). |
| `queue_depth_p95`, `queue_depth_max` | harness-side queue from `harness/lanes.yaml`. |
| `provider_retry_rate`, `provider_5xx_rate`, `provider_429_rate` | from `pheno/harbor_util.py` retry log. |
| `harness_overhead_ms` | time from request to model `forward()` call. |

### 3.4 Composite (kept compatible with `eval/route_matrix.py`)

```
composite = 0.40 · score_agent_quality
          + 0.30 · score_serving
          + 0.30 · score_harness_quality
```

The **route kinds** get extended from
`{omniroute_cloud, local_direct, omniroute_combo}` to also include
`local_only` and `hybrid_n` (N-agent parallel sweeps).

---

## 4. Suite → benchmark → harness wiring

### 4.1 TB2.0 (canonical, already wired)

- Path: `eval/tbench.py` — extended to drop the runner choice via
  `--runner {ik_llama, vllm, sglang, trtllm, mlx}`.
- Tasks: `terminal-bench@2.0` (89 tasks).
- Honors `n_attempts=1` and holdout-exclusion policy already in
  `config/eval_pillars.yaml`.

### 4.2 TB2.1 (NEW)

Same harness; tasks `terminal-bench@2.1`. Pin the *exact* revision in a
config hash so we can reproduce.

### 4.3 TB3.0 (compatibility watch)

A stub is added now (`eval/suites/tbench_3_0/`) that detects the upstream
shipped revision; the body reads from the live tbench.ai template rather
than pinning tasks. Auto-disabled if upstream schema changes during a run.

### 4.4 DeepSWE (NEW)

```
eval/suites/deepswe/
├── deepswe_pack.yaml           # Pier version pin + provider config
├── loader.py                    # resolves / 113 tasks, joins harbor_util
├── runner.py                    # pier run --env modal|docker; per-task verifier
└── README.md
```

Key constraints: Pier ≥ 0.3.0 (per DeepSWE README), separate-verifier since
v1.1, `--env modal` for parallel sandboxes is supported. We default to
`--env docker` locally to keep disk + spend in check.

### 4.5 SWE-bench Verified / Lite (NEW regression baseline)

```
eval/suites/swe_bench_verified/
├── loader.py                    # downloads verified split; verify SHA256
├── runner.py                    # per-instance harness container
└── README.md
```

Constraints: the standard SWE-bench harness reads
`{"model_patch", "test_patch"}` and a Dockerfile; we wrap that into a
Harbor task shape so `eval/harbor_util.py` can run it.

`SWE-bench Lite` is the fast smoke regression: 300 instances → run nightly,
not per PR.

### 4.6 Long-horizon custom tasks (NEW)

These are Harbor-shaped tasks we author, **separately from any external
benchmark** to avoid contamination (see `RISKS.md` §1):

- **cross_repo_refactor** — given N linked repos, change a shared API,
  keep build + tests green across all N.
- **compiler_migration** — port a piece of code across toolchains.
- **eval_pipeline_construction** — build a tiny eval harness, score on a
  held-out fixture.
- **multi_service_patch** — change a route + handler + tests + docs in one
  patch, all services must pass their respective suites.

### 4.7 Harness quality suite (NEW)

For each agent task suite (TB2.1, DeepSWE, long-horizon), pair the run
with `chat_loop_baseline` vs `intent_graph_v1` and emit the differential
metrics defined in §3.2. Same prompts, same model id — only the harness
configuration differs.

### 4.8 Verbosity suite (NEW)

Run the same task suite three times per model: a verbose vs terse system
prompt, plus a `pass@k_recovery` mode where we give the agent N chances
inside one budget. Output:
`tokens_per_success_at_5_$`, `pass_at_k_curve`.

### 4.9 Per-role eval suite (NEW — see also `TRACE_EVALSET_PLAN.md`)

Each role has its own **minimum-viable-similar-bench**:

- solo_engineer — TB2.1 + DeepSWE-13 (curated 13).
- coding_subagent — small focused subset of TB2.1 `easy` tier, 5-min caps.
- reviewer — diff review + intent classification on real PRs from
  traces repo.
- planner_manager — multi-step task with explicit advance/replan events.
- qa_test_agent — fix-tests-only mode on synth defects.
- perf_profiler_agent — instrumented app + demand a delta; success = the
  model explains where time went in pl-l1 terms.
- release_integration_agent — full release dry-run against `eval/`.
- advisor_sponsor — blind critique of another run's trace.

---

## 5. Self-improvement loop — garden model

Today's pipeline is sequential: run TB2 → write nightly DPO → distill 12B →
train sub-1B → loop. That has two failure modes:

- One-day-lag: by the time we see a regression, the loop already trained on
  it.
- Single-signal: reward is one number (`acceptance`).

The plan replaces the chain with a **garden**: a continuously-populated
ledger where each trace is a seed, each gate is a weed, and growth is
replay-driven.

```
         ┌─────────────────────┐
         │  trace recorder    │   (every model call, tool call, diff,
         │  append-only JSONL │    test, retry, denial, cache-hit, metric)
         └─────────┬───────────┘
                   │
       ┌───────────▼────────────┐
       │  per-role feature      │   (per-role featurization; same
       │  extractor             │    schema for solo_engineer / advisor /
       └───────────┬────────────┘    reviewer / ... regardless of source)
                   │
       ┌───────────▼────────────┐
       │  week-grain ledger     │   (success rate, cost-per-success,
       │  (WORM per role)       │    recovery, denial, regression — by role)
       └───────────┬────────────┘
                   │
       ┌───────────▼────────────┐
       │  gating simulator      │   (P-vs-R, σ-σ, regression-1SLO,
       │  parallel replay       │    replay-equiv, denial-rate — all the
       └───────────┬────────────┘    gates in §6 of IMPLEMENTATION_PLAN)
                   │
       ┌───────────▼────────────┐
       │  promotion / demotion  │   (promoted → nightly DPO;
       │  and authorship audit  │     demoted → reverted; every change is
       └─────────────────────────┘    attributable to a trace id)
```

### 5.1 Properties the garden enforces

| Property | How |
|---|---|
| **Every change has a trace.** | Promotion requires at least one trace id per signal that justifies it. |
| **Never trust a single signal.** | Reward = `weighted(multi_signal)` with weights per `eval/nested_rlvr.py` L0/L1/L2/L3. |
| **Weed before you grow.** | Demotion fires automatically on regression (see `IMPLEMENTATION_PLAN.md` §6). |
| **Retention is bounded.** | `bench/results/` and `eval/results/` age-prune (default 14 d); raw trace JSONL goes to cold storage keyed by `eval_id`. |
| **Authorship audit.** | Model name + runner + lane + verifier id + git SHA, all attached to every promotion. |

### 5.2 What this replaces in pheno-harness today

| Today | Garden replacement |
|---|---|
| `scripts/nightly_dpo.py` | `scripts/gardener.py` (single source of promotion / weeding). |
| `scripts/train_sub1b.py`, `scripts/distill_12b.py` | Same scripts, called only with promotion tokens. |
| `verifier/harness.py` as gatekeeper | now also a **signal source**; gate stays but its decisions are recorded. |
| `traces/ingest.py` | unchanged; consumed by the ledger. |

---

## 6. Performance profiler

The profiler is the most instrumental of the suites and is its own thing,
not "two more YAML files". Concretely:

```
eval/perf/
├── profiler.py                   # 1-Hz sampler; psutil + pynvml + runner-stats pull
├── harness_overhead.py           # tags each frame as harness vs model vs IO
├── ctx_cache_probe.py            # fires repeated-prefix variants; reports hit% by prefix-shape
├── parallel_sweep.py             # N ∈ {1,2,4,8,16} agent-fleet sweep on the host
└── README.md
```

**Sampling rules** (so we don't get nonsense):

| Channel | Source | Why |
|---|---|---|
| `gpu_util`, `vram_peak` | `pynvml`, `nvidia-smi --query-gpu=…` | pinned to PID when multi-process. |
| `cpu_util` | `psutil.Process(pid).cpu_percent()` | per-process, **not** `top`. |
| `ram_peak` | `psutil.virtual_memory().used` | host-level is fine on a one-machine setup. |
| `disk_io_mb`, `disk_free` | `psutil.disk_io_counters`, `shutil.disk_usage` | for the 2 TB fullness signal. |
| `ctx_cache_hit_rate` | runner-side logs (vLLM, SGLang, ik_llama, TRT-LLM) | runner-specific key extraction lives in `eval/perf/runner_stats.py`. |
| `queue_depth` | harness lanes queue (`harness/lanes.yaml`) | emitted by `pheno/model_manager.py`. |

**Default cap:** 5 min micro-eval per cell. Reproducibility: same
`cfg+commit+model+runner+profile+env` hash.

The profiler also tags every wall-time slice as **model**, **harness**, or
**io** so we can separately report:

- `harness_overhead_ms = time before forward() call`
- `provider_latency = time from send to first byte of model output`
- `tokens_time = decode time inside runner`

---

## 7. Trace recorder (foundations)

The trace recorder writes to `eval/traces/<run_id>.jsonl` with one event
per line:

```json
{
  "ts": "2026-07-03T15:24:18.041Z",
  "run_id": "...",
  "lane": "routine",
  "role": "solo_engineer",
  "kind": "model_call" | "tool_call" | "diff" | "test_result" | "denial" |
          "cache_hit" | "retry" | "metric" | "outcome",
  "payload": { ...kind-specific... },
  "trace_meta": { "config_hash": "...", "commit_sha": "...", "model_id": "...", "runner": "..." }
}
```

This is the input to `TRACE_EVALSET_PLAN.md`; without it, we cannot derive
per-role data, gate tests, or replay.

---

## 8. Implementation ladder

| PR | What | Why |
|---|---|---|
| PR-1 | perf profiler + trace recorder (instrument only) | evidence before edits |
| PR-2 | DeepSWE pack + Pier runner | first hard long-horizon benchmark |
| PR-3 | SWE-bench Verified / Lite adapter | regression baseline |
| PR-4 | Long-horizon custom Harbor-compatible tasks | coverage without contamination |
| PR-5 | Engine adapters (SGLang, vLLM, TRT-LLM, MLX) | covered in `MODEL_MATRIX.md` |
| PR-6 | Per-role eval pipeline (uses ingested traces) | closes `TRACE_EVALSET_PLAN.md` loop |
| PR-7 | Harness-quality differential runner | chat-loop vs intent-graph |
| PR-8 | Verbosity + N-agent sweep | closes perf triangle |
| PR-9 | Garden: ledger + gating simulator + authorship audit | closes self-improvement loop |

The first six land before the chat-loop is touched. See `IMPLEMENTATION_PLAN.md`
for sequencing and acceptance criteria.
