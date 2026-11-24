# IMPLEMENTATION_PLAN.md

> **Status:** Staged plan with concrete first PRs. Builds on `RESEARCH_AUDIT.md`, `EVAL_ARCHITECTURE.md`, `TRACE_EVALSET_PLAN.md`, `MODEL_MATRIX.md`, `RISKS.md`.
> **Naming convention:** forks we own use `-dev` in bin/path names (`forge-dev`, `omniroute-dev`, `pheno-serve-dev`, `codex-dev`). Canonical source: `docs/ARCHITECTURE_LAYERS.md`.
> **Model SKUs:** the active local-only lock is exactly `local/qwen35-08b`, `local/lfm25-8b-a1b`, and `local/ornith-8b`. The broader shortlist is historical research and does not authorize downloads or evaluation.
> **Eval suites (primary):** Terminal-Bench 2.0/2.1, DeepSWE, custom long-horizon Harbor-compatible — per ADR 0005 §"Eval-suite posture". **SWE-bench Verified / Lite demoted to debug-only regression signal** (not in main sweep). See `state/hf_scrape/2026-07-04/cost_projection.md` for per-suite cost × run-count projections.
> **Cloud baseline routing:** disabled by the active local-only policy. The future architecture remains `forge-dev → omniroute-dev → OpenRouter`, but current execution is self-hosted only: `pheno-serve-dev` → SGLang/vLLM/llama.cpp.
> **Recency cutoff:** 2026-03-01 per ADR 0004 rule #6 and ADR 0005. Models older than that require explicit justification.
> **Self-hosted scope:** exactly 3 aliases per ADR 0005 — `local/qwen35-08b`, `local/lfm25-8b-a1b`, and `local/ornith-8b`.
> **Execution rule:** No PR merges core harness changes without a benchmark artifact in `bench/results/`.

---

## 0. Stages

| # | Stage | Type | Depends on |
|---|---|---|---|
| 1 | TB 2.0 + 2.1 + custom long-horizon driver (primary eval lane) | Eval | nothing |
| 2 | DeepSWE integration (113 tasks, separate-verifier post-v1.1) | Eval | Stage 1 |
| 3 | Intent-graph Stage A — passive recording | Harness | nothing |
| 4 | Perf suite (`perf/*`) | Harness + serving | Stage 3 |
| 5 | Self-improvement loop (`harness/self_improvement/`) | Meta | Stage 1 + Stage 2 + Stage 3 + Stage 4 |
| 6 | Model × engine matrix sweep | Eval + serving | Stage 4 |
| 7 | Trace-derived per-role eval set | Eval | Stage 3 |
| 8 | Intent-graph Stage B–E (deterministic tools, planning, multi-agent, strong re-entry) | Harness | Stage 3 + Stage 7 |
| 9 | SWE-bench Verified / Lite (debug-only regression; NOT in main sweep) | Eval | Stage 5 |
| 10 | Codex fork migration (gated) | Repo | **gated on user sign-off after Stage 2 or 6** |

---

## 1. Stage 1 — TB 2.0/2.1 + custom long-horizon driver (primary eval lane)

**Why first:** pheno-harness's `eval/tbench.py` already runs TB 2.0 honestly. Adding 2.1 is a one-driver extension. The custom long-horizon Harbor-compatible suite fills the gap between short TB tasks and full DeepSWE work. TB 3.x is a watch (pre-release); not in primary lane.

**Per-stage cost ceiling (from `state/hf_scrape/2026-07-04/cost_projection.md`):**
- TB 2.0 full sweep (89 tasks × 11 picks × n=1) = $1,596.91; per pick = $145.17.
- TB 2.1 full sweep = $1,758.31; per pick = $159.85.
- Custom long-horizon (4h×30 tasks × 11 picks × n=1) = $5,797.50; per pick = $527.05.
- Stage 1 combined ceiling = ~$9,153 (n=1) or ~$36,612 (n=4 attempts).

**Files to add / modify:**

- **NEW** `pheno-harness/eval/tbench_v21.py` — local-first Terminal-Bench 2.x driver; defaults to the currently published `terminal-bench@2.0` and accepts `@2.1` only when Harbor publishes it.
- **NEW** `pheno-harness/eval/tbench_v3_watch.py` — gated by `PHENO_ENABLE_TB3=1`. Skips by default. Logs a daily "TB 3.x compat" status row.
- **MODIFY** `pheno-harness/config/harbor_tbench_models.yaml` — add `terminal-bench@2.1` and `terminal-bench@3.x` task lists under new keys `tb21_tasks` and `tb3_tasks`.
- **MODIFY** `pheno-harness/eval/HARBOR.md` — note TB 2.1 status + TB 3.x watch.

**Acceptance:**
- `python scripts/run_tbench_v21.py --subset 16` produces a `terminal-bench@2.0` manifest with the acquired local task-artifact hash when available.
- `python scripts/run_tbench_v21.py --subset full` exits 0 on dry-run (no real model call needed; just task binding).
- TB 3.x watch writes a one-line "compat status" row daily.

**Risk:** TB 2.1 task list may not yet be in the Harbor registry on the day of run. Mitigation: fall back to TB 2.0 if TB 2.1 is missing; report `tbench_21_status: missing` in the run manifest.

**Subagent use:** none. Single-agent work; depends on pheno-harness internals.

---

## 2. Stage 2 — DeepSWE integration

**Why after Stage 1:** DeepSWE uses a separate verifier (post-v1.1) and Pier ≥ 0.3.0 — driver pattern follows TB 2.0/2.1 but adds Pier plumbing. 113 tasks across TS/Go/Python/JS/Rust.

**Per-stage cost ceiling (from `state/hf_scrape/2026-07-04/cost_projection.md`):**
- DeepSWE full sweep (113 × 11 picks × n=1) = $9,402.45; per pick = $854.77.
- Pier sandbox cost is separate (Modal or similar); budget $200 for a 16-task subset probe first.
- Stage 2 combined ceiling = ~$9,402 (n=1) or ~$37,610 (n=4).

**Files to add:**

- `pheno-harness/eval/deepswe.py`
- `pheno-harness/config/deepswe_models.yaml`
- `pheno-harness/scripts/run_deepswe.py`
- **MODIFY** `pheno-harness/pheno/harbor_util.py` — handle DeepSWE's separate verifier (post-v1.1) and Pier ≥ 0.3.0 requirement.

**Acceptance:**
- `python scripts/run_deepswe.py --subset 16 --env modal` produces `bench/results/deepswe/<run_id>.json`.
- Pier version pinned in `requirements` block; missing Pier aborts the run with a clear error.

**Subagent use:** **partial.** Driver can be built in parallel with Stage 6; the run itself is serial.

---

## 3. Stage 3 — Intent-graph Stage A (passive recording)

**Why now:** zero behavior change. We add observability so all future eval runs produce a `.graph.json` that intent-graph Stages B–E will execute against. No destabilization risk.

**Files to add / modify:**

- **NEW** `pheno-harness/harness/intent_graph/__init__.py`
- **NEW** `pheno-harness/harness/intent_graph/recorder.py` — wraps every tool call and model call into a typed graph node.
- **NEW** `pheno-harness/harness/intent_graph/dag.py` — DAG node/edge schema (see `EVAL_ARCHITECTURE.md` §4.2).
- **MODIFY** `pheno-harness/pheno/harbor_util.py` — call recorder at every tool/model boundary.
- **MODIFY** `pheno-harness/eval/tbench.py`, `eval/route_matrix.py` — emit `<run_id>.graph.json` after each run.

**Acceptance:**
- Re-run `python scripts/run_tbench_route_matrix.py --subset 4` and confirm `bench/results/tbench/<run_id>.graph.json` exists and is valid JSON.
- Replay the `.graph.json` against a different model binding produces a comparable trace (still metrics-instrumented; not yet plan-execution).

**Subagent use:** none. Core-harness change; main thread only.

---

## 4. Stage 4 — Perf suite

**Why here:** depends on Stage 2's recorder for harness_overhead measurement.

**Implemented baseline:**

- `perf/resources.py` — optional psutil + `nvidia-smi` sampler with mean/peak telemetry.
- `perf/streaming.py` — OpenAI-compatible SSE TTFT and chunk-proxy ITL.
- `perf/sweep.py` — actual in-flight concurrency levels with failure retention.
- `scripts/run_perf_suite.py` — warmups, resource overhead, synthetic mode, and JSON report.
- `config/model_engine_matrix.yaml` — local model × engine/decode axes.
- `config/disk_budget.yaml` — non-destructive admission policy.

Cache-hit counters and engine-native queue/cache telemetry remain a follow-up
integration once a local server exposes those fields; the profiler labels those
metrics absent rather than fabricating them.

**Acceptance:**
- `python scripts/run_perf_suite.py --synthetic ...` validates scheduling without a model call.
- Against a local endpoint it writes TTFT, chunk-proxy ITL, tokens/sec, warmup/failure rows, probe overhead, and resource peaks.
- Cache-hit and queue fields are absent until supplied by the selected engine, never inferred.

**Probe overhead reporting:** every probe run is paired with a no-probe reference run. Diff is reported in the manifest as `probe_overhead_ms`.

**Subagent use:** **yes.** Each probe file is small and independent. Dispatch one subagent per file. Main thread composes `perf/report.py`.

---

## 5. Stage 5 — Self-improvement loop

**Why here:** depends on Stage 1 (signals), Stage 2 (per-turn record), Stage 3 (resource signals).

The brief explicitly contrasts "just told to RLVRAF" with a **garden-managed** loop. The observation-only spine is now implemented in `harness/self_improvement/`: signal aggregation, fail-closed gates, non-destructive retention preview, and two-window human-gated promotion decisions. It does not mutate routing, prompts, weights, or training policy.

**Implemented files:**

- `harness/self_improvement/__init__.py`
- `harness/self_improvement/signals.py` — numeric aggregates by optional role/lane key.
- `harness/self_improvement/gates.py` — holdout, regression, safety, budget, reproducibility, and serving-stability gates.
- `harness/self_improvement/retention.py` — non-destructive 30-day retention preview.
- `harness/self_improvement/promotion.py` — two consecutive green windows plus human approval; never mutates state.
- `scripts/run_self_improvement_tick.py` — daily dry-run entrypoint.

**Acceptance:**
- `python scripts/run_self_improvement_tick.py --dry-run` reads the last 7 days of ledger observations, applies all required gates, and reports pass/fail per lane without mutating state.
- A synthetic failing run (intentionally injected) trips the regression gate.
- A synthetic unsafe run (intentionally injected) trips the safety gate.

**Subagent use:** the implementation was audited and then completed in the main worktree after delegated workers disconnected.

**Loop tick (daily, cron):**
1. Aggregate last 24 h of eval results.
2. Run all gates.
3. If any gate fails → emit a "garden alert" with the failing lane + role + diff vs. previous tick. **No automatic promotion.**
4. If all gates pass for two consecutive ticks → emit a "promotion candidate" row. Promotion still requires human approval via PR.

This is the "garden-managed" property: the loop observes and proposes, a human (or a meta-model with risk budget) decides.

---

## 6. Stage 6 — Model × engine matrix sweep

**Why after the perf suite:** depends on the perf suite, the matrix YAML, and a stable SGLang/vLLM/TRT-LLM toolchain.

**Per-stage cost ceiling:** self-hosted only — no OR token cost. The cost is **disk + GPU-hours**:
- 11 picks × T0–T4 × 4 engines = ~176 cells; ~5 min per cell = ~15 GPU-hours single-shot.
- n_attempts=3 → ~45 GPU-hours.
- Self-hosted weights: Qwen3.5 0.8B, LFM2.5 8B-A1B, and Ornith 8B alias only. Qwen/LFM Q4 artifacts and the published grafted Ornith MTP Q4 artifact are now hash-locked; no BF16 local assumption for large models.

**Files to add / modify:**

- **MODIFY** `pheno-harness/scripts/kv_bakeoff.py` — extend to a full T0–T4 × engine matrix.
- **MODIFY** `pheno-harness/scripts/run_tbench_model_matrix.py` — same.
- **NEW** `pheno-harness/config/m1_fallback.yaml` — MLX / llama.cpp worker for M1 Pro.
- **NEW** `pheno-harness/scripts/run_m1_fallback_smoke.py`

**Acceptance:**
- Per-tier sweep writes one row per (model, engine, quantization) cell.
- M1 Pro smoke writes one row per (model, format) cell.
- All rows tagged with the full reproducibility manifest.

**Subagent use:** **yes.** Each tier (T0, T1, T2, T3, T4, T5, M1) can be a separate subagent. Main thread joins the results into `bench/results/perf/<date>_matrix_summary.json`.

---

## 7. Stage 7 — Trace-derived per-role eval set

**Why after Stage 2:** the intent-graph recorder makes per-turn replays possible.

**Implemented baseline:**

- **MODIFY** `traces/ingest.py` — `infer_role(event)`, minimum-evidence eligibility checks, Codex session discovery, and explicit non-scoreable public-analysis indexing.
- **NEW** `eval/role_suite.py` — review-only spec/replay builder and role-count manifest.
- **NEW** `scripts/build_trace_spec.py` — converts one JSONL trace to a spec + replay pair.
- **NEW** `scripts/run_role_eval.py` — manifest-first review runner; model execution remains disabled.

Approval, PII/secret review, holdout split, golden replay, and actual
model-backed execution remain gated after review artifacts exist.

**Acceptance:**
- 30 approved specs in `bench/fixtures/trace_replay/`.
- 4 role suites scoring: `solo_engineer`, `coding_subagent`, `reviewer`, `planner_manager`.
- All reviewed replays emit `.graph.json` when execution is enabled.

**Subagent use:** **partial.** Spec classification is a script. Spec review is human. Golden runs are serial.

---

## 8. Stage 8 — Intent-graph Stages B–E

**Why last:** full architectural transition. Stages A and B reduce cost without behavior change; C–D add the planner and multi-agent fan-out; E adds strong re-entry.

**Files to add (over Stages 2):**

- `pheno-harness/harness/intent_graph/planner.py`
- `pheno-harness/harness/intent_graph/tools.py` — deterministic tool registry.
- `pheno-harness/harness/intent_graph/scheduler.py`
- `pheno-harness/harness/intent_graph/replay.py`

**Acceptance per sub-stage:**
- **B:** deterministic tool execution reduces cost ≥ 20 % vs. chat-loop baseline (measured on TB 2.0 16-task subset).
- **C:** planner emits a valid DAG on ≥ 80 % of TB 2.0 tasks; failure falls back to chat loop.
- **D:** sub-agent fan-out reduces wall time ≥ 30 % on tasks with ≥ 3 independent reads.
- **E:** strong re-entry fires only on `post` predicate failure; recovers ≥ 50 % of such failures.

**Subagent use:** **partial.** Tools can be parallelized. Planner is main-thread (it touches the core chat loop).

---

## 9. Stage 9 — SWE-bench Verified / Lite (debug-only regression, NOT in main sweep)

**Why demoted:** per ADR 0005 §"Eval-suite posture". SWE-bench Verified / Lite skew older and instrumented differently than our primary lane (TB 2.0/2.1/DeepSWE/long-horizon). Keep as **debug-only** to validate harness plumbing changes; do NOT include in main weekly sweep.

**When invoked:** only when (a) a harness plumbing change needs a cross-check, (b) a regression in TB 2.0 + DeepSWE is suspected to be env-specific (not model-specific).

**Per-stage cost ceiling:**
- SWE-bench Verified frozen 200-task subset × 11 picks × n=1 = $3,180 (rough).
- SWE-bench Lite 300-task × 11 picks × n=1 = $4,770 (rough).
- Stage 9 is **not in default weekly cadence** — explicit opt-in per run.

**Files to add / modify:**
- `pheno-harness/eval/swebench_verified.py` — frozen 200-task subset.
- `pheno-harness/eval/swebench_lite.py` — full 300-task run.
- `pheno-harness/scripts/run_swebench_regression.py` — gated by `--allow-swebench-regression` flag (default false).
- **MODIFY** `pheno-harness/training/eval_holdout.yaml` — add SWE-bench Verified subset to holdout.

**Acceptance:**
- `python scripts/run_swebench_regression.py --allow-swebench-regression` produces `bench/results/swebench/<run_id>.json` with `pass@1`, `regressions`, and per-task wall time.
- Default invocation (without flag) exits 0 with a printed notice that SWE-bench is debug-only.

**Subagent use:** **yes.** Driver + runner can be built in parallel with other Stage 9 work.

---

## 10. Stage 10 — Codex fork migration (gated)

**Gating:** user sign-off required after **Stage 2 (DeepSWE)** or **Stage 6 (matrix sweep)** completes successfully. Do not start without explicit approval.

**Scope (preview):**
- Mirror Stages 1–9 against the codex fork.
- Same eval suites; different harness substrate.
- The matrix YAML, the trace-derived evalset, the perf suite, and the self-improvement loop transfer; the intent-graph Stages B–E require codex-internal refactors.

---

## 11. First PRs (concrete, ordered)

PRs are sized so each one is benchmarkable end-to-end.

| PR | Title | Files | Stages | Risk |
|---|---|---|---|---|
| #1 | `audit: research + architecture deliverables` | `audit/*.md` | — | none (docs only) |
| #2 | `eval(tbench): TB 2.1 driver + TB 3.x watch + long-horizon driver (primary eval lane)` | `eval/tbench_v21.py`, `eval/tbench_v3_watch.py`, `eval/long_horizon.py`, `config/harbor_tbench_models.yaml`, `eval/HARBOR.md` | 1 | low |
| #3 | `eval(deepswe): DeepSWE driver (113 tasks, Pier ≥ 0.3.0)` | `eval/deepswe.py`, `config/deepswe_models.yaml`, `scripts/run_deepswe.py` | 2 | low |
| #4 | `harness: passive intent-graph recorder (Stage A)` | `harness/intent_graph/{recorder,dag}.py`, `pheno/harbor_util.py`, `eval/{tbench,route_matrix}.py` | 3 | low |
| #5 | `perf: add TTFT/ITL/cache/harness-overhead/parallel probes` | `perf/*`, `scripts/run_perf_suite.py`, `config/model_engine_matrix.yaml` | 4 | low |
| #6 | `harness: self-improvement gates + retention + promotion` | `harness/self_improvement/*`, `scripts/run_self_improvement_tick.py`, `config/eval_pillars.yaml` | 5 | medium |
| #7 | `eval+perf: full model × engine matrix sweep` | `config/model_engine_matrix.yaml`, `config/m1_fallback.yaml`, scripts | 6 | medium |
| #8 | `eval: per-role trace suite + spec builder` | `traces/ingest.py`, `eval/role_suite.py`, scripts, fixtures | 7 | medium |
| #9 | `harness: intent-graph Stages B–E` | `harness/intent_graph/{planner,tools,scheduler,replay}.py` | 8 | high |
| #10 | `eval: SWE-bench Verified + Lite (debug-only, gated)` | `eval/swebench_{verified,lite}.py`, `scripts/run_swebench_regression.py`, `training/eval_holdout.yaml` | 9 | low |
| #11 | **GATED:** codex fork migration of Stages 1–9 | TBD | 10 (gated) | TBD |

---

## 12. Acceptance / verification gates per PR

Per the brief's "every benchmark run must be reproducible from config, commit hash, model id, provider, hardware profile, and environment variables":

- Each PR adds or extends `bench/results/<suite>/<run_id>.manifest.json` and a `scoreboard.md` roll-up.
- Each PR runs the existing suite baseline **before** and **after** the change and includes both manifests in the PR description.
- A PR that regresses any pillar score in `config/eval_pillars.yaml` by more than the threshold is auto-blocked.
- A PR that introduces a new dependency updates `requirements.txt` (or equivalent) and is verified to install cleanly on a fresh Windows + Python environment.

---

## 13. Subagent dispatch plan

Parallelizable work goes to subagents via the `task` tool. The main thread always owns:

- Core harness changes (intent-graph Stages B–E, recorder integration).
- The eval scoreboard roll-up.
- The reproducibility contract enforcement.

Subagents own:

- Independent driver implementations (Stage 3 probes, Stage 5/6 eval drivers).
- Per-tier model sweeps (Stage 7).
- Independent self-improvement modules (Stage 4 signals / gates / retention / promotion).
- Spec pipeline stages (Stage 8 T1–T7, with T3 review as human gate).

Subagent hand-off contract: each subagent returns file paths (relative to `pheno-harness/`) and a 5-line summary. Main thread composes the scoreboard from those artifacts.

---

## 14. Roll-out calendar (suggested)

| Week | Focus | Exit criteria | Cost ceiling |
|---|---|---|---|
| W1 | PR #1, #2 | TB 2.1 + long-horizon drivers run; TB 3.x watch reports daily | ~$9,153 (n=1) / ~$36,612 (n=4) |
| W2 | PR #3 | DeepSWE 16-task subset live with Pier sandbox | ~$1,330 (16-task probe) |
| W3 | PR #4 | `.graph.json` produced by every eval run | $0 (recorder only) |
| W4 | PR #5 | First perf-suite numbers published for one T1 cell | $0 (self-hosted) |
| W5 | PR #6 | Self-improvement tick dry-run is green on synthetic data | $0 |
| W6 | PR #7 | First matrix sweep (T0 + T1 + Qwen3.5-0.8B) complete | ~22 GB disk + ~5 GPU-hours |
| W7 | PR #8 | 30 approved trace specs + 4 role suites scoring | ~$2,000 (custom role-suite probe) |
| W8 | PR #9 (B) | Deterministic tools reduce TB 2.0 cost ≥ 20 % | $0 (perf-only) |
| W9 | PR #9 (C–D) | Planner + multi-agent fan-out live; TB 2.0 wall time −30 % on multi-read tasks | $0 |
| W10 | PR #9 (E) | Strong re-entry live; recovery rate measured | $0 |
| W11 | PR #10 — opt-in only | SWE-bench Verified cross-check run IF a TB regression is suspected | ~$3,180 (200-task × 11 picks) |
| W12 | PR #11 — **gated** on user approval | codex fork plan signed off per ADR 0005 (post Stage 2 or 6 only) | — |

This is a suggestion, not a contract. Slack in W4/W5/W6 is expected as the perf suite reveals hardware limits. **The cost ceilings are first-pass projections** — refine after Stage 1 ships actual numbers; current assumptions are documented in `state/hf_scrape/2026-07-04/cost_projection.md`.
