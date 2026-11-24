# TRACE_EVALSET_PLAN.md

> **Status:** Design. Builds on `pheno-harness/traces/` ingest (already implemented).
> **Goal:** Convert the user's collection of long-running agent traces into a replayable, per-role eval set that measures task success, harness quality, and serving performance for each role independently.

---

## 0. What we already have

- `pheno-harness/traces/ingest.py` — multi-source ingest (OmniRoute SQLite, forge history, codex, claude, cursor, factory droid).
- `pheno-harness/traces/motion.py` — per-trace motion signals (turn count, tool distribution, escalation frequency).
- `pheno-harness/traces/wastage.py` — wastage analysis (token waste, redundant tool calls, retry storms).
- `pheno-harness/eval/results/{wastage_latest, harbor_latest, tbench_route_probe, tbench_model_scores, budget_latest}.json` — schema templates for new suites.

What we don't have is a **per-role eval pipeline** that scores individual roles (planner, reviewer, QA, perf, integration, advisor, etc.) the way `tbench.py` scores the whole agent.

---

## 1. Trace sources (priority order)

1. **Local Claude traces** — `~/.claude/projects/**/*.jsonl` (read-only mirror; do not modify).
2. **Local Codex traces** — `~/.codex/sessions/**/*.jsonl`.
3. **Local ForgeCode traces** — `~/forge/state/sessions/**/*.jsonl` (if present).
4. **Local Factory Droid traces** — `~/.factory/sessions/**/*.jsonl` (if present).
5. **Local Cursor-agent traces** — `~/.cursor/agent-logs/**/*.jsonl` (if present).
6. **Public analyses** — long-running orchestrator chats, multi-agent transcripts from arXiv/blog posts (corpus under `D:\koosh\Downloads\`).
7. **Pheno-harness's own traces** — `bench/results/tbench/<run_id>.trace.jsonl` and `<run_id>.graph.json` (produced once intent-graph Stage A lands).

**Selection rule:** traces must contain (a) a recognizable multi-role structure (planner + ≥ 1 sub-agent), (b) at least 30 turns total, (c) at least one recovery or escalation event, (d) a verifiable terminal outcome (commit, test pass/fail, ship/no-ship).

---

## 2. Per-role taxonomy

Roles are inferred from message metadata + content + tool calls. Each role has a stable string key.

| `role_id` | What it does | Tool-call signature | Prompt style |
|---|---|---|---|
| `solo_engineer` | Whole-agent on a single coherent task. No fan-out. | mixed: read, edit, test, build, search | high-level task brief |
| `coding_subagent` | Receives scoped sub-task; writes/edits code; runs tests; reports back. | read, edit, test, search, build | narrow, with file paths + acceptance criteria |
| `reviewer` | Reads a diff or patch; comments on correctness/style/security. | read, search, sometimes test | "review this patch" |
| `planner_manager` | Decomposes a goal into a DAG; assigns roles; tracks progress. | search, read, sometimes edit for todo lists | high-level goal + constraints |
| `planner_sponsor` | Same as `planner_manager` but for advisory-only mode (does not edit code). | search, read | high-level goal + history |
| `qa_test` | Writes/runs tests; reports coverage and regressions. | test, read, search | "make sure X is true" |
| `perf_profiler` | Runs profiling tools, reads metrics, suggests optimizations. | read, search, run_perf tools | "find the bottleneck in X" |
| `release_integration` | Bundles, bumps versions, opens PRs, writes changelogs. | edit, run_release_tools, read | "ship v0.x" |
| `advisor_critic` | Pure advisory; no edits. Comments and questions. | read, search | "is this a good idea?" |

**Inference rules (in priority order):**
1. Explicit `role: <id>` in the trace metadata (used by pheno-harness and forge-dev).
2. Tool-call signature matches a known role pattern (e.g. test-only role → `qa_test`).
3. Prompt header matches a known pattern (e.g. starts with "Review this diff" → `reviewer`).
4. Falls back to `solo_engineer` if none of the above match.

Inference is **never destructive**: traces that can't be confidently role-tagged go into a `bench/fixtures/trace_replay/_unclassified/` bucket and are reviewed by hand before use.

---

## 3. Schema for the trace-derived evalset

Two artifacts per replayable task:

### 3.1 `<task_id>.spec.json` — the replayable spec

```json
{
  "task_id": "trace_replay_2026-03-12_codereview_ling_flask_001",
  "source": {
    "origin": "claude",
    "trace_path": "/abs/original/trace.jsonl",
    "trace_sha256": "<redacted>",
    "captured_at": "2026-03-12T15:04:11Z",
    "captured_model": "<original model id>",
    "captured_provider": "<original provider>"
  },
  "task_kind": "code_review",
  "role_id": "reviewer",
  "brief": "Review the diff in PR #4231 against repo policy.",
  "context": {
    "repo": "flask",
    "pr_number": 4231,
    "base_sha": "<redacted>",
    "head_sha": "<redacted>",
    "files_changed": ["src/flask/app.py", "src/flask/blueprints.py"]
  },
  "constraints": {
    "max_turns": 12,
    "max_wall_s": 600,
    "max_cost_usd": 0.25,
    "max_tokens_in": 60000,
    "max_tokens_out": 12000
  },
  "verification": {
    "kind": "human_label",
    "human_label": {
      "pass": true,
      "rubric": "review_3_or_more_issues_and_one_strength",
      "notes": "..."
    },
    "fallback_verifier": {
      "kind": "llm_judge",
      "judge_model": "<redacted>",
      "judge_prompt_sha256": "<redacted>",
      "judge_min_score": 0.7
    }
  },
  "metadata": {
    "domain": "code_review",
    "language": "python",
    "difficulty": "easy|medium|hard",
    "long_horizon": false,
    "tags": ["reviewer", "python", "flask"]
  }
}
```

### 3.2 `<task_id>.replay.jsonl` — the deterministic replay script

One JSON object per turn of the original trace, in order. Each object is a typed instruction the harness executor can fulfill deterministically OR delegate to a model.

```jsonl
{"turn": 1, "kind": "model_call", "role_id": "reviewer", "messages": [...], "tools_allowed": ["read", "search"], "temperature": 0.0}
{"turn": 2, "kind": "tool_call", "tool": "read", "args": {"path": "src/flask/app.py", "offset": 120, "limit": 40}, "expected_output_kind": "file_slice"}
{"turn": 3, "kind": "assertion", "predicate": "review_mentions_at_least_3_issues", "severity": "soft"}
{"turn": 4, "kind": "model_call", "role_id": "reviewer", "messages": [...], "tools_allowed": ["read", "search"]}
...
```

`kind ∈ {model_call, tool_call, assertion, scoring, checkpoint}`.

Replays are **not** strict re-enactments — they are *reference trajectories*. The eval executor is allowed to deviate as long as the assertions at the end pass and the cost/turn budgets hold. This lets us swap models without re-running the original human trace.

---

## 4. Replay executor (in `pheno-harness/eval/role_suite.py`)

Pseudo-code:

```python
def run_role_replay(spec: TaskSpec, model_binding: ModelBinding) -> RunResult:
    rec = Recorder(spec.task_id, model_binding)
    state = ReplayState()
    for turn in spec.replay:
        if turn.kind == "model_call":
            response = call_model(turn.messages, model_binding, tools=turn.tools_allowed)
            rec.add_turn(turn, response)
            state.apply(response)
        elif turn.kind == "tool_call":
            result = deterministic_tool_registry.execute(turn.tool, turn.args)
            rec.add_turn(turn, result)
            state.apply(result)
        elif turn.kind == "assertion":
            pred_result = evaluate_predicate(turn.predicate, state)
            rec.add_assertion(turn, pred_result)
            if not pred_result.passed and turn.severity == "hard":
                state.fail(turn.predicate)
        elif turn.kind == "checkpoint":
            rec.checkpoint(state.snapshot())
        elif turn.kind == "scoring":
            score = score_turn(state, turn.rubric)
            rec.add_score(score)
    return rec.finalize(spec)
```

**Three guarantees the executor must hold:**
1. **Determinism of non-model steps.** `tool_call` and `assertion` are reproducible from the same `replay.jsonl` + same repo state.
2. **Budget enforcement.** Hard stop when `constraints` are exceeded. Run is marked `failed:budget_exceeded`.
3. **Trace recording is non-negotiable.** Every turn emits an entry; the run is rejected by the scoreboard if any turn is missing.

---

## 5. Metric emission per role

For each role suite run, the scoreboard row contains:

| Field | Notes |
|---|---|
| `task_id` | from spec |
| `role_id` | from spec |
| `pass` | final assertion |
| `wall_s`, `turns`, `tool_calls`, `tokens_in`, `tokens_out`, `cost_usd` | standard |
| `soft_assertions_passed / total` | partial-credit signal |
| `hard_assertions_passed / total` | required for pass |
| `recoveries` | times the model got back on track after a failed assertion |
| `escalations` | times the harness re-entered a strong model from a weak worker |
| `first_failure_turn` | turn index of first failed assertion (lower = less recoverable) |
| `final_state_kind` | `pass | fail:assertion | fail:budget | fail:crash | fail:tool_error` |
| `role_specific_metrics` | per-role extras (see below) |

### 5.1 Role-specific extras

| Role | Extras |
|---|---|
| `solo_engineer` | `patch_loc`, `tests_added`, `regressions` |
| `coding_subagent` | `patch_loc`, `tests_added`, `first_pass_test_rate` |
| `reviewer` | `issues_count`, `false_positive_rate`, `false_negative_rate` |
| `planner_manager` | `dag_depth`, `dag_width`, `branch_count`, `dead_ends` |
| `planner_sponsor` | `advice_alignment_score`, `unsolicited_edit_attempts` |
| `qa_test` | `tests_added`, `coverage_delta`, `false_failures` |
| `perf_profiler` | `metric_deltas`, `regressions_introduced` |
| `release_integration` | `manifest_correct`, `tag_present`, `changelog_loc` |
| `advisor_critic` | `advice_actionable_score`, `factual_error_rate` |

The first cut ships the four roles the user named most often: `solo_engineer`, `coding_subagent`, `reviewer`, `planner_manager`. The other five follow once the suite proves out.

---

## 6. Trace → spec pipeline

Stages, all small and independent:

1. **Stage T1 — collect.** Script scans the source paths listed in §1, hashes each trace, copies to `bench/fixtures/trace_replay/_inbox/`. Reject if any source path is modified after copy.
2. **Stage T2 — classify.** `traces/ingest.py` extended with `infer_role(trace) -> role_id`. Runs over `_inbox/`. Produces `bench/fixtures/trace_replay/_classified/<task_id>.json` per trace.
3. **Stage T3 — review.** Hand-review the classified list. Filter out traces that (a) leak secrets, (b) contain PII, (c) are too short (< 30 turns), (d) lack a verifiable outcome. Move survivors to `bench/fixtures/trace_replay/_approved/`.
4. **Stage T4 — spec build.** `scripts/build_trace_spec.py` converts an approved trace into a `<task_id>.spec.json` + `<task_id>.replay.jsonl` pair. Stores both in `bench/fixtures/trace_replay/`.
5. **Stage T5 — holdout split.** A random 20 % of approved traces are reserved as the role-eval holdout (mirror of `training/eval_holdout.yaml` logic). Never used for training.
6. **Stage T6 — golden run.** First execution on the strongest available model becomes the golden baseline. Stored as `bench/fixtures/trace_replay/_golden/<task_id>.golden.json`.
7. **Stage T7 — dry-run validation.** Replay the golden on three random model bindings (cheap → strong → local) and confirm the executor produces a valid trace + valid assertions. If any binding crashes the executor, fix the executor before adding more specs.

Each stage writes a status file to `bench/fixtures/trace_replay/_state/<stage>.json` so the pipeline is resumable.

---

## 7. Per-role scoreboards

Five scoreboards, one per role, each with the metric set from §5.

```
bench/results/role_eval/<role_id>/
    <YYYY-MM-DD>_run.json
    latest.json
    scoreboard.md       # human-readable roll-up
```

Promotion rules (in `harness/self_improvement/promotion.py`):
- A model/lane is eligible for promotion into `<role_id>` only if:
  - `pass ≥ pass_threshold` (per role; from `config/eval_pillars.yaml`)
  - `wall_s ≤ wall_s_budget`
  - `cost_usd ≤ cost_budget`
  - `soft_assertions_passed / total ≥ soft_threshold`
  - `first_failure_turn` distribution is non-degrading vs. last promotion

---

## 8. Corpus anchors used

These ChatGPT-* files directly informed the per-role design and metric choices:

- `D:\koosh\Downloads\ChatGPT-Coding Agents and Intent Graphs (1).md` — planner role decomposition.
- `D:\koosh\Downloads\ChatGPT-Agent Flow Optimization.md` — parallel branch handling for `planner_manager`.
- `D:\koosh\Downloads\ChatGPT-Feature graph system design.md` — DAG schema basis.
- `D:\koosh\Downloads\ChatGPT-Agent-Aware Speculative Decoding.md` — shared-prefix optimization that benefits `coding_subagent` + `reviewer` patterns.
- `D:\koosh\Downloads\ChatGPT-Concurrent Lint Command Handling.md` — `qa_test` and `release_integration` deterministic tool design.
- `D:\koosh\Downloads\ChatGPT-RLVR-AF Optimization Proposal (1).md` — `release_integration` reward shaping.
- `D:\koosh\Downloads\ChatGPT-LatentMAS vs TextMAS comparison (1).md` — `advisor_critic` text-MAS path (latent parked).

---

## 9. Scale targets

For the program to be statistically meaningful, each role suite needs at least:
- 30 approved specs at first cut
- 80 approved specs at v1.0
- 200 approved specs at v2.0

Sourced roughly:
- 50 % from local Claude traces (most prolific source)
- 25 % from Codex / ForgeCode / Factory Droid / Cursor combined
- 15 % from public analyses
- 10 % from pheno-harness's own traces once intent-graph Stage A is live

If local trace volume is insufficient, augment with **synthetic traces** generated by a strong model running the planner role against Harbor TB2 tasks. Synthetic traces must be marked `synthetic: true` in the spec and never used for training.

---

## 10. What this plan does **not** cover

- Live A/B testing across users. Out of scope.
- User-facing leaderboard. Out of scope (until promoted).
- Open-weights dataset release. Defer; coordinate with the spec submodule.
- Latent-MAS role encoding. Parked; see `EVAL_ARCHITECTURE.md` §9.