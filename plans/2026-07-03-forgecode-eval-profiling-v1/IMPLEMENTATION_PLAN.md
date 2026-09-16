# IMPLEMENTATION_PLAN.md

Date: 2026-07-03
Companion to: `RESEARCH_AUDIT.md`, `EVAL_ARCHITECTURE.md`,
`MODEL_MATRIX.md`, `TRACE_EVALSET_PLAN.md`, `RISKS.md`.

Staging plan for the eval + profiling program. Each PR is small,
benchmarkable, and safe to land without destabilizing the harness core.

---

## 1. Sequencing principle

> **Instrument first, study second, edit behavior only when evidence
> supports it.**

Every PR-1..PR-9 adds observability or a benchmark. **Only PR-10**
touches the chat-loop. The chat-loop edit is gated by the gate
simulator (see §6), which requires evidence gathered from PR-1..PR-9.

This is the direct response to the user's note that the prior version
of pheno-harness was "just told to RLVRAF." We don't tell; we measure
and gate.

---

## 2. Staged PRs

### PR-1 — Profiler + trace recorder (instrument only)

**Files added:**
- `eval/perf/profiler.py` — 1 Hz sampler (psutil + pynvml).
- `eval/perf/harness_overhead.py` — tags wall-slices.
- `eval/perf/runner_stats.py` — runner-specific cache-hit extraction.
- `eval/perf/ctx_cache_probe.py` — repeated-prefix variants.
- `eval/perf/parallel_sweep.py` — N ∈ {1,2,4,8,16} fleet size sweep.
- `eval/traces/recorder.py` — JSONL append-only writer (the recorder).
- `pheno/instrument.py` — context-manager hooks for the recorder
  (does not change chat-loop semantics).

**Files modified:**
- `scripts/run_playground.py` — opt-in `--record-trace`.
- `config/context_caps.yaml` — cap any single trace at 100 MB so disk
  pressure is bounded.

**Acceptance:**
- One micro-eval (5 min) produces a recorder JSONL **and** a profiler
  CSV. Both readable by humans, both parseable.
- No chat-loop behavior change (set `instrument=True` flag only).

### PR-2 — DeepSWE pack + Pier runner

**Files added:**
- `eval/suites/deepswe/deepswe_pack.yaml` — Pier ≥ 0.3.0 pin, provider.
- `eval/suites/deepswe/loader.py` — resolves 113 tasks, joins
  `pheno/harbor_util.py`.
- `eval/suites/deepswe/runner.py` — `pier run --env docker|modal`.
- `eval/suites/deepswe/README.md`.

**Acceptance:**
- One micro-eval (5 min) of 3 DeepSWE tasks passes the verifier split.
- Reproducibility: `cfg + commit + pier_ver + model_id + runner` hash
  matches across N=3 replays.

### PR-3 — SWE-bench Verified / Lite adapter

**Files added:**
- `eval/suites/swe_bench_verified/loader.py`.
- `eval/suites/swe_bench_verified/runner.py`.
- `eval/suites/swe_bench_lite/...` — 300-instance smoke regression.

**Acceptance:**
- Lite 5-min smoke on a single instance passes.
- Verified can take hours; gated behind `--allow-long` opt-in, default
  off, default budget cap applied.

### PR-4 — Long-horizon custom Harbor-compatible tasks

**Files added:**
- `eval/suites/long_horizon/cross_repo_refactor/`.
- `eval/suites/long_horizon/compiler_migration/`.
- `eval/suites/long_horizon/eval_pipeline_construction/`.
- `eval/suites/long_horizon/multi_service_patch/`.

Each suite has `loader.py`, `runner.py`, `README.md`, and a
`contamination_check.py` that asserts the task **has no overlap** with
TB2.0/2.1/3.0 and DeepSWE (per `RISKS.md` §1).

### PR-5 — Engine adapters (SGLang, vLLM, TRT-LLM, MLX)

Sub-PRs in order:
- **PR-5a** MLX on M1 Pro (`bench/smoke_mlx.py`).
- **PR-5b** SGLang on Windows; load Qwen4B + 0.6B draft.
- **PR-5c** vLLM on Windows; reproduce prefix-cache hit in `ctx_cache_probe.py`.
- **PR-5d** TRT-LLM compile-once smoke (Qwen4B).
- **PR-5e** Custom CUDA kernel slot (only if spec-dec parity requires).

Acceptance per sub-PR is in `MODEL_MATRIX.md` §9.

### PR-6 — Per-role eval pipeline

Files added per `TRACE_EVALSET_PLAN.md`:
- `eval/per_role/<role>.py` — 8 featurizers.
- `eval/roles/coverage_report.py`.
- `eval/roles/run.py`.
- `eval/synthetic/` synthetic generator.

Acceptance is `TRACE_EVALSET_PLAN.md` §10.

### PR-7 — Harness-quality differential runner

- `eval/harness_quality/chat_loop_baseline/`.
- `eval/harness_quality/intent_graph_v1/` — **does not change chat-loop
  yet**; only measures against the same chat-loop by tagging the
  `events` to "would-have-been" intent-graph frontiers.
- `eval/harness_quality/deterministic_tool_only/`.
- `eval/harness_quality/rerank_only/`.
- `eval/harness_quality/scoring.py` — emits differential metrics.

### PR-8 — Verbosity + N-agent sweep

- `eval/suites/verbosity/...` (3 prompts × models).
- `eval/suites/perf_profile/n_agent_parallel_throughput.py`.

### PR-9 — Garden (ledger + gates + authorship audit)

- `eval/ledger/` — append-only, WORM semantics.
- `eval/gardener/gating_simulator.py`.
- `scripts/gardener.py` — single source of promotion / weeding.
- `verifier/harness.py` extended to record its decisions.
- Authorship audit table per change (`model_id + runner + lane + verifier_id
  + git SHA`).

### PR-10 — Intent-graph / scheduler refactor (gated)

**This is the chat-loop edit.** It is the largest single change and is
intentionally last. Gate conditions are in §6.

- `pheno/planner.py` — planner produces typed DAG.
- `pheno/dag.py` — DAG type, frontier ops, replan.
- `pheno/scheduler.py` — parallel + serial dispatcher.
- `pheno/context_bundle.py` — context bundler prevents long-chat pollution.
- `harness/lanes.yaml` — extended with `dag_lane` and
  `deterministic_tool_lane`.

---

## 3. Branch strategy

| Branch | Purpose |
|---|---|
| `main` | protected, gated; the eval + profiling program is built here, no chat-loop edits until PR-10. |
| `eval/profiling-v1` | PR-1..PR-9. |
| `eval/garden-v1` | PR-9. |
| `core/intent-graph-v1` | PR-10 only; gated by §6. |

Rules:
- **No PR merged to `main` without `pytest eval/per_role/test_register.py`
  green** for whichever per-role artifact it touches.
- **No PR merged without the recorder JSONL** in `eval/traces/<run_id>.jsonl`
  if it produces a runnable artifact.

---

## 4. CI gates (proposed for `pheno-harness` repo)

`.forge/workflows/eval-gates.yml` (new):

```yaml
name: eval-gates
on: [pull_request]
jobs:
  gates:
    runs-on: self-hosted     # the eval host has 3090 Ti
    steps:
      - uses: actions/checkout@v4
      - name: pytest registries
        run: pytest eval/per_role/test_register.py -q
      - name: smoke eval (5 min cap)
        run: python scripts/run_playground.py --suite tbench_2_1 --budget 5 --instrument
      - name: gate checks
        run: python -m eval.gardener.gating_simulator --gate p-vs-r --window 7d
      - name: deny-on-regression
        run: python -m eval.gardener.deny_check
```

Failure of any step blocks merge.

---

## 5. Acceptance ladder (so stage 2 — codex fork — only opens when stage 1 passes)

| Gate | Held by | Verified by |
|---|---|---|
| Profiler + recorder land | PR-1 | profiler smoke + 1 traced run. |
| First long-horizon benchmark runs | PR-2 + PR-3 | DeepSWE + SWE-bench Verified smoke. |
| Engine parity (matrix has actual numbers) | PR-5 | model_matrix JSONL has every cell, including failures. |
| Per-role eval opens | PR-6 | 8 roles, ≥ `min sample size`, leaderboard emits. |
| Garden gates real decisions | PR-9 | at least one promotion / one demotion by evidence. |
| Stage 1 ships | PR-1..PR-9 | ledger row count > 0 across all suites. |

When all gates are green, **stage 2 (codex fork)** opens; the
`IMPLEMENTATION_PLAN-stage2.md` is its sibling doc, written when stage 1
lands.

---

## 6. The chat-loop gate (PR-10 must satisfy before landing)

These are derived from `EVAL_ARCHITURE.md` §3.2 (harness quality plane).
**Every** one must be true for PR-10:

| Gate | Definition | Source |
|---|---|---|
| **G1** | `acceptance_delta` (intent-graph − chat-loop) ≥ +5% on TB2.1 micro. | `eval/harness_quality/scoring.py` |
| **G2** | `steps_per_success` ≤ chat-loop baseline on ≥ 3 of 5 long-horizon tasks. | same |
| **G3** | `replay_reproducibility` ≥ 90% of runs. | recorder + replay. |
| **G4** | `denied_action_rate` ≤ 0.1% rise (and never zero, because that means the gate is not firing). | `verifier/risky_action.py`. |
| **G5** | No regression in `oracle_timeout_rate` (per role). | profiler. |
| **G6** | No regression in `cost_per_success` (per role). | ledger. |
| **G7** | No increase in `orphan_tool_calls`. | ledger. |

If any gate fails, PR-10 demotes automatically. This is the **only**
mechanism by which the chat-loop changes.

---

## 7. Self-improvement loop, concretely

```
recorder.jsonl
   │
   ▼
per-role featurizer (PR-6)
   │
   ▼
ledger (PR-9; WORM append-only; rows per (role, model, lane) per day)
   │
   ▼
gating_simulator (PR-9)
   │  - p-vs-r: pass-rate vs regression σ
   │  - σ-σ: cost-per-success stability
   │  - replay-equiv: same cfg→same outcome
   │  - rejection: denied actions when gate is on
   │
   ▼
promotion / demotion
   │  - promote: nightly DPO / distill / train_sub1b
   │  - demote: revert; record reason + trace id
   ▼
authorship ledger (PR-9)
```

Specific signals (multi-signal reward, not one number):

| Signal | Weight default | Where computed |
|---|---|---|
| acceptance | 0.40 | verifier |
| cost-per-success | 0.20 | ledger |
| replay-equiv | 0.10 | replay runner |
| denied-actions (≥ 0) | 0.05 | verifier/risky_action.py |
| regression-1SLO | 0.10 | ledger |
| recovery-curve | 0.05 | ledger |
| verbosity | 0.05 | ledger |
| human-critic correlation (advisor only) | 0.05 | per-role |

Weights come from `eval/nested_rlvr.py` macros (`L0..L3`) which already
exist. Adjustable per role.

### 7.1 Why this beats "just told to RLVRAF"

- Multi-signal, not single.
- Gates prevent regression before promotion, not after.
- Promotion requires evidence, not a one-day-old pipeline run.
- Demotion is **automatic** when any G1..G7 fails.
- Audit trail is per-change, not per-day.

---

## 8. Architectural intent-graph plan (this is PR-10, sketched early)

Why: chat-loop pollutes context, can't parallelize independent leaves,
and forces every step to pay a "strong model" tax. The intent-graph
plan replaces it with:

- **Planner**: a strong model produces a **typed DAG** (typed =
  each node is one of `read | grep | test | build | run-lint | …
  decide`).
- **Deterministic tools**: search/read/test/build run as leaves, not as
  chat. Where the tool can replace the model, it does.
- **Weak/local workers**: leaf tasks (e.g. "run pytest on file X")
  execute on T1/Qwen4B, not on the strong model.
- **Strong model re-entry**: only on ambiguity, design choices, failed
  tests, or review.
- **Scheduler**: independent leaves run in parallel, up to `lanes.yaml`
  bandwidth cap.
- **Recorder**: every model call, tool call, file diff, test result,
  metric, denial is captured as a `recorder.jsonl` event.
- **Context bundle builder**: prevents long-chat pollution and supports
  replayable evals; same bundle + same model = same outcome up to
  stochasticity.

The result is faster, cheaper, more parallel, more auditable — and
**measurable** before and after by the differential metrics in
`EVAL_ARCHITECTURE.md` §3.2.

---

## 9. Out-of-scope for this plan

- Re-architecting the Forge Rust crates (`forge-cli` et al.). The plan
  works against the existing harness.
- Choosing a long-term winner among engines. We're measuring, not picking.
- Open-sourcing new benchmarks. Authored tasks live in this repo and are
  used internally; public release is a separate decision.
- Hardware purchase. The plan respects the 24 GB ceiling.
