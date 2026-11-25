# TRACE_EVALSET_PLAN.md

Date: 2026-07-03
Companion to: `EVAL_ARCHITECTURE.md`, `MODEL_MATRIX.md`,
`RESEARCH_AUDIT.md`, `IMPLEMENTATION_PLAN.md`, `RISKS.md`.

Goal: turn the heterogeneous agent traces we already have (or can pull)
into an evalset that scores **per role**, not per chat. Roles are the
short list the brief asked for; the schema and the pipeline are the
focus here, not the specific traces.

Pheno-harness already has `traces/ingest.py` for multi-source ingest. We
extend it, not replace it.

---

## 1. Source traces (target list)

| Source | Local? | Path / endpoint | Role coverage |
|---|---|---|---|
| Forge / forge-cli history | yes | `forge/.forge/state/*.jsonl` and `forge/logs/*.jsonl` | mixed; mostly solo_engineer + coding_subagent. |
| Codex | yes (logs in `forge-work` style dirs) and via `collect_traces.py` exports | `eval/traces/source/codex/*.jsonl` | coding_subagent, reviewer. |
| Claude | no local (only screenshots/chats) — fetchable if API allowed | `eval/traces/source/claude/*.jsonl` | advisor_sponsor, planner_manager, solo_engineer. |
| Factory Droid | yes (via claude-code-style exports) | `eval/traces/source/droid/*.jsonl` | coding_subagent, qa_test_agent. |
| Cursor-Agent | yes (via local exports of composer/chat diffs) | `eval/traces/source/cursor/*.jsonl` | coding_subagent, performance/profiler_agent. |
| Public long-running orchestrator analyses | no (read-only) | github gists / blog posts | used to **augment** role taxonomy, not as a scored source. |

**Important:** local-only sources are scored openly; remote sources are
sanitized first (re-author, hash PII) before they go into the ledger
(see `RISKS.md` §4).

---

## 2. Why per-role, not per-chat

The brief explicitly asks for this. Per-chat scoring conflates:

- how good the *prompt* was (cheap to keep raising),
- how good the *router* was (forks chat into roles),
- how good the *role-specific guidance* was (LoRA / system prompt).

Per-role scoring exposes all three and gives us the lever we actually
want: optimize the model skill on a real role, then move on.

---

## 3. Roles (canonical)

Each role is **defined**, not inferred. A role is `{name, scope, success
criteria, eval harness, scoring formula}`.

### 3.1 solo_engineer

- **Scope:** take an issue, write the patch, run tests, summarize.
- **Success:** patch passes the issue's verifier (TB-style) within budget.
- **Eval harness:** TB2.1 + DeepSWE-curated subset.
- **Scoring:** `pass@1` × `cost_per_success`.

### 3.2 coding_subagent

- **Scope:** implement a single file or module under explicit spec.
- **Success:** tests for the touched files pass; no regressions outside
  the touched files.
- **Eval harness:** micro-eval on `eval/suites/swe_bench_lite/`
  per-file subsets.
- **Scoring:** `pass@1` × `acceptance_speed` (tokens-to-green).

### 3.3 reviewer

- **Scope:** critique an existing diff, find defects, suggest fixes.
- **Success:** defect recall ≥ baseline (defined vs. human-labeled set).
- **Eval harness:** `eval/suites/role_perf/reviewer/` — public PR-derived
  diffs + human-labelled defects, N=200.
- **Scoring:** `recall@k` × `false_positive_rate`.

### 3.4 planner_manager

- **Scope:** read task, propose plan, advance/replan as evidence arrives.
- **Success:** typed DAG completed with every step green; no orphan
  steps; replan events fired only when evidence justifies.
- **Eval harness:** `eval/suites/role_perf/planner_manager/` —
  cross_repo_refactor and multi_service_patch.
- **Scoring:** DAG valid × steps green × replan-correctness.

### 3.5 qa_test_agent

- **Scope:** write or fix tests to cover known faults.
- **Success:** tests added reach the fault (oracle-confirmed).
- **Eval harness:** synthetic defect injection on small repos.
- **Scoring:** fault coverage × regression introduced.

### 3.6 perf_profiler_agent

- **Scope:** explain where time/memory goes, propose a single change.
- **Success:** explanation names the right hot-path (validated against
  `bench/results/kv_bakeoff`-style artifacts).
- **Eval harness:** instrumented toy apps + demand a delta.
- **Scoring:** hot-path accuracy × delta_applied_passes.

### 3.7 release_integration_agent

- **Scope:** full release dry-run: changelog, version bump, CI green,
  tag, dry deploy.
- **Success:** dry-run succeeds end-to-end without manual intervention
  or harness denial-due-to-over-reach.
- **Eval harness:** `eval/suites/role_perf/release_integration_agent/`.
- **Scoring:** completion × denial-budget-left.

### 3.8 advisor_sponsor

- **Scope:** read another agent's trace, give one-paragraph critique.
- **Success:** critique names a defect the model would actually fix.
- **Eval harness:** blind A/B against human critic, N=200.
- **Scoring:** judge-correlation × critique-length-cost.

---

## 4. Trace schema (canonical)

Single JSONL schema, **role-agnostic** at the source so we can retag
later without rewriting the ingest:

```json
{
  "ts": "2026-07-03T15:24:18.041Z",
  "run_id": "abc-123",
  "source": "forge" | "codex" | "claude" | "droid" | "cursor" | "synthetic",
  "lane": "routine" | "ci" | "architecture" | "medium_hard" | "research" | "rollout",
  "role": "solo_engineer" | "...",
  "model_id": "...",
  "runner": "ik_llama" | "vllm" | "sglang" | "trtllm" | "mlx" | "openrouter",
  "config_hash": "...",
  "commit_sha": "...",
  "events": [
    {
      "kind": "user" | "system" | "assistant" | "tool_call" | "tool_result" |
              "diff" | "test_result" | "denial" | "retry" | "cache_hit" |
              "metric" | "outcome",
      "ts_offset_ms": 12,
      "payload": { "...": "..." }
    }
  ],
  "outcome": {
    "verdict": "pass" | "fail" | "timeout" | "budget_exceeded" | "denied",
    "tests": { "added": 0, "passed": 0, "failed": 0, "flaky": 0 },
    "tokens_in": 0, "tokens_out": 0,
    "wall_ms": 0, "turns": 0,
    "step_count": 0,
    "verifier_id": "...",
    "patch_size_lines": 0
  },
  "trace_meta": { "...": "..." }
}
```

This is the source of truth for the role-perf scores. Performance
metrics are derived (not part of the trace) to keep the trace stable.

---

## 5. Pipeline

```
[raw sources]
   │
   ├── forge/.forge/state/*.jsonl  ─┐
   ├── codex exports               ─┤
   ├── claude exports              ─┤   traces/ingest.py (already exists)
   ├── droid exports               ─┤   → eval/traces/raw/*.jsonl
   ├── cursor exports              ─┤
   └── synthetic                   ─┘
                                        │
                            ┌───────────▼────────────┐
                            │ normalizer             │
                            │ - lift role lane model │
                            │ - canonicalize event   │
                            │ - tag outcome          │
                            │ - redact PII           │
                            └───────────┬────────────┘
                                        │
                            ┌───────────▼────────────┐
                            │ deduper / partitioner  │
                            │ - by config_hash       │
                            │ - by model_id          │
                            │ - by run_id (replays)  │
                            └───────────┬────────────┘
                                        │
                            ┌───────────▼────────────┐
                            │ per-role featurizer    │
                            │ - per role from §3     │
                            │ - emits parquet per role
                            └───────────┬────────────┘
                                        │
                            ┌───────────▼────────────┐
                            │ eval runner            │
                            │ - rerun model          │
                            │ - replay trace         │
                            │ - emit per-role score  │
                            └───────────┬────────────┘
                                        │
                            ┌───────────▼────────────┐
                            │ ledger writer (garden) │
                            └────────────────────────┘
```

Two **production rules**:

1. **Re-author before scoring.** If we don't have the original model
   output, we don't score. (Re-running the same `model_id + config_hash`
   is fine; re-running on a *different* model is not the same trace.)
2. **Replay-equiv gate.** Each trace can be replayed; replays must match
   ±5% for the trace to enter the ledger (see
   `IMPLEMENTATION_PLAN.md` §6.4).

---

## 6. Featurizers (per role)

For each role, a small Python module under `eval/per_role/<role>.py`:
- takes the JSONL events,
- emits tabular parquet columns,
- raises `UnknownRole` if the trace can't be featurized (we don't tag
  by gut; we **fail loud**).

This is the surface where new roles are added — never featurize by string
munging the event stream in two places.

---

## 7. Synthetic complement

Public traces are finite and skewed (e.g. Claude dominates long-horizon,
Droid dominates code-only). We need a synthetic complement for:

- roles that almost never appear in public traces (`perf_profiler_agent`),
- adversarial settings the public source can't offer (under denial,
  under replay, under cache-miss),
- roles attached to **this repo** (`release_integration_agent`) where the
  ground truth is the harness itself.

Synthetic generator lives at `eval/synthetic/` and tags every event with
`synthetic=true` so the ledger can exclude it from any leaderboard
without losing it from training.

---

## 8. Coverage matrix (target)

| Role | Real trace source | Synthetic complement | Min sample size |
|---|---|---|---|
| solo_engineer | forge, codex, droid | long_horizon/* | 500 |
| coding_subagent | forge, codex, cursor | swe_bench_lite per-file | 500 |
| reviewer | codex, claude | code-review public PRs | 200 |
| planner_manager | claude, forge | cross_repo_refactor | 100 |
| qa_test_agent | codex, cursor | synthetic defect injection | 200 |
| perf_profiler_agent | cursor | instrumented toy apps | 50 |
| release_integration_agent | forge (CI logs) | dry-run synthetic | 50 |
| advisor_sponsor | claude | human-critic blinds | 100 |

If a role falls below `min sample size`, the leaderboard for that role
flags it as `n_insufficient`.

---

## 9. What we **don't** do

- We don't try to fix the prompt of the source model. We replay.
- We don't score on chat-only aggregates. Roles are first-class.
- We don't accept un-tagged or un-normalized traces. Fail loud.

---

## 10. Acceptance criteria for PR-6 (per-role eval pipeline)

| Acceptance | How verified |
|---|---|
| All 8 roles have a featurizer. | `pytest eval/per_role/test_register.py` |
| All 8 roles have ≥ `min sample size` real or synthetic traces. | `python -m eval.roles.coverage_report` |
| Per-role leaderboard emits one JSON per run with envelope + per-role scores. | `python -m eval.roles.run --roles all --out eval/results/roles_<ts>.json`. |
| Replay-equiv gate holds for ≥ 90% of real traces. | Replay runner report. |
| Ledger receives every run. | `eval/ledger/...` row count grows with each run. |
