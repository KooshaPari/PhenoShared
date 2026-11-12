# dagrun Traceability

What dagrun records about a plan node, where that record lives, and which
questions the persisted record can answer today. Every row cites the file that
was read; nothing here is inferred from naming or documentation.

Run directory is `--dir`, default `.dagrun` (`main.go:24`). It is created with
`trace/` and `logs/` subdirectories (`internal/store/store.go:91-92`); the
installed plan is `run.yaml` (`cmd_plan.go:112`, read back by `openRun`,
`main.go:274`).

## 1. The trace surface as implemented

The trace is a set of append-only JSONL shards, one per worker, under
`<dir>/trace/`. Each line is a `trace.Event` (`internal/trace/trace.go:20-31`):
`ts`, `run`, `node`, `worker`, `event`, `epoch`, `attempt`, `exit`, `dur_ms`,
`msg`, `attrs`. Writers append to their own shard so processes never contend
(`Writer.Emit`, `internal/trace/trace.go:46`); `trace.Merge` reads every
`*.jsonl` in the directory and returns events sorted by timestamp, skipping a
torn tail line rather than failing the whole view (`internal/trace/trace.go:127-178`).

Producers are in `internal/run/`: `run.start` / `run.end` (`run.go:139,337`),
`node.claim`, `node.worktree`, `node.spawn`, `node.exit`, `node.<status>`,
`node.adopt`, `lease.reap`, `lease.lost`, `provider.cooldown` (`run.go:147,271,568,577`;
`exec.go:69,135,158,326,364,375`; `expand.go:52,80`; `usage.go:133`; `hooks.go:54`).

| Subcommand | Implemented in | Reads | Writes |
|---|---|---|---|
| `dagrun trace` | `cmd_view.go:261` (`cmdTrace`) | merged `<dir>/trace`; filters `--node`, `--event`, `--since`, `--limit` | stdout only: rendered text via `trace.Render`, or one JSON event per line with `--json`. Writes no file. |
| `dagrun export` | `cmd_view.go:302` (`cmdExport`) | installed plan, `state.json` snapshot, merged trace | file via `--out` or stdout; `--format agileplus\|tracera\|json` (`internal/export/export.go:72,124,228+`) |
| `dagrun review` | `cmd_report.go:56` (`cmdReview`) | plan, `state.json` snapshot, merged trace (`report.ReviewRun`, `internal/report/report.go:197`) | stdout, or file via `--out` (`RenderReview`, `report.go:347`). Note: the flag help says "default REVIEW.md" but the code prints to stdout when `--out` is empty — a documented-vs-actual mismatch, no defect in the record itself. |
| `dagrun critique` | `cmd_report.go:19` | installed plan only (`report.CritiquePlan`, `report.go:73`) | stdout, or file via `--out`. No trace input. |
| `dagrun timeline` | `cmd_timeline.go:15` | merged `<dir>/trace` (`trace.Merge`, line 23) | stdout, or JSON (`timeline.Build`, line 27) |

`dagrun gc` is advertised as pruning "old logs, traces, and merged worktrees"
(`main.go:152`); its implementation was not read for this document and is not
asserted here.

## 2. The artifact-gate surface

Artifacts are declared per node in the plan (`plan.Node.Artifacts`,
`internal/plan/plan.go:81`) and verified by `verify.PlanNode`
(`internal/verify/verify.go:68`), whose package doc states the rule: a node is
done only when every declared artifact satisfies its predicate **and** the
optional check command exits 0; nothing asks a model or trusts a claim.

Concretely, `PlanNode` (`verify.go:75-110`):

1. runs `checkArtifact(root, a)` for every entry in `n.Artifacts`; each yields an
   `ArtifactResult` with `path`, `ok`, `code`, `detail`, `files`, `bytes`,
   `sha256`, `matches` (`verify.go:24-33`);
2. runs `PlanKindCheck(n, root, p)` for cross-node contracts (a TEST must
   reference requirement ids of a SPEC it depends on; a node must not claim a
   parallel sibling's artifact);
3. runs `n.Check` inside `n.Workdir` when a check command is declared, producing
   `CheckResult{command, ok, exit_code, output, duration_ms, timed_out}`.

Command entry points:

- `dagrun done NODE` (`cmd_node.go:53`) calls `verify.PlanNode`, refuses on
  failure unless `--force`, then persists via `store.Force(n.ID, StatusDone,
  reason, &rep, now)`. A forced done records `reason = "forced done by operator"`
  in `LastError` (`cmd_node.go:80-82`).
- `dagrun fail|skip` (`cmd_node.go:92-121`) write status and a free-text
  `--reason` into `LastError` via the same `Force`.
- `dagrun claim NODE` (`cmd_node.go:14`) calls `store.Claim`, which enforces
  dependency order, terminal state, the attempt budget from
  `plan.EffectiveAttempts`, and both concurrency caps (`internal/store/lease.go:97-156`).
- `dagrun validate` (`cmd_node.go:123`) re-runs `verify.PlanNode` over every node
  and reports `broken` (recorded done but no longer verifies) and `adoptable`
  (satisfied but not marked done).

## 3. The durable record

Under `<dir>` (default `.dagrun`):

| Path | Written by | Format |
|---|---|---|
| `run.yaml` | `cmd_plan.go:112` | installed plan, the original YAML |
| `state.json` | `store.writeState` (`store.go:179`) | one JSON document: `version`, `run`, `plan_hash`, `created_at`, `updated_at`, `nodes` map, `dynamic` (`store.go:53-62`) |
| `state.json` → per-node `NodeState` | `Claim`, `Finish`, `Force`, `RecordUsage`, `SetFailureClass`, `Annotate` | `status`, `attempts`, `epoch`, `owner`, `lease_until`, `started_at`, `finished_at`, `exit_code`, `worktree`, `branch`, `usage`, `failure_class`, `duration_ms`, `last_error`, `verify` (`store.go:31-51`) |
| `lock` | `store.go:243,282` | advisory lock around every state mutation |
| `trace/<worker>.jsonl` | `trace.Writer.Emit` | JSONL, one `Event` per line |
| `logs/<node>/<unixnano>.log` | `internal/run/exec.go:100` | raw child stdout/stderr |

State mutations are guarded: `Finish` and `RecordUsage` only apply when
`ns.Owner == owner && ns.Epoch == epoch` (`lease.go:196-222`, `223-240`), so a
zombie child cannot overwrite its successor's result. `Force` bypasses
ownership (`lease.go:272-288`).

## 4. Traceability matrix

Question: can I answer X from the persisted record alone?

| Question | Answer | Grounded in |
|---|---|---|
| Which node ran? | YES | `state.json` `nodes` keys plus `trace/*.jsonl` `node.*` events (`trace.go:20-31`, `run.go:271`) |
| When did it run? | YES | `NodeState.started_at` / `finished_at` / `duration_ms` (`store.go:37-48`); `Event.ts` |
| Under which harness / provider / model? | PARTIAL | plan fields only (`plan.Node.Harness/Provider/Model`, `plan.go:73-75`) in `run.yaml`; `NodeState` has no harness/provider/model field (`store.go:31-51`); the spawn event stores only the harness binary name in `msg` (`exec.go:135`). Provider appears only in `provider.cooldown` `attrs` (`exec.go:326`). |
| What artifacts did it produce? | YES | `NodeState.Verify.Artifacts[]` with `path`, `bytes`, `sha256` (`verify.go:24-33`, written by `Finish`/`Force`) |
| Was the artifact verified? | YES | `Report.OK` and `ArtifactResult.OK` (`verify.go:39-45`); `dagrun validate` re-checks (`cmd_node.go:123`) |
| Who claimed it? | PARTIAL | `Claim` sets `NodeState.Owner` (`lease.go:140`), but `Finish` and `Force` clear it to `""` (`lease.go:203,279`), so a completed node has no owner in `state.json`; `cmdClaim` emits no trace event, and the trace `node.claim` writer records only the run's owner label (`run.go:271`) |
| Why did it fail? | YES | `NodeState.LastError`, `FailureClass`, `Verify.Reason`, `ExitCode` (`store.go:39-50`), plus `node.fail` trace event with `msg` (`run.go:577`) |

Counts: 7 questions — 5 YES, 2 PARTIAL, 0 NO.

## 5. Gaps

**G1 — harness/provider/model is not attributable per run attempt (PARTIAL, row 3).**
Only the plan's intent is stored; a retry that routes to a different provider is
invisible. Smallest change: populate `trace.Event.Attrs` on the existing
`node.spawn` emit (`exec.go:135`) with `harness`, `provider`, `model` resolved at
spawn time; `Attrs` already exists and is already serialised.

**G2 — claim attribution is erased on completion (PARTIAL, row 6).**
`Finish`/`Force` set `Owner = ""`, so "who claimed it" is unrecoverable after
the fact, and agent-driven `dagrun claim` leaves no trace at all. Smallest
change: stop clearing `Owner` and add a separate lease field, or emit a
`node.claim` event from `cmdClaim` with `worker` = the claiming owner.

**Noted, not a matrix gap:** `dagrun review`'s `--out` help advertises a default
`REVIEW.md` while the code prints to stdout when `--out` is empty
(`cmd_report.go:56-77`). The record is unaffected; only the help text is wrong.

Status: draft, authored 2026-11-12T12:27Z from module state at commit 128b9f1982a96fe9e90f8c0130176d84b862a52a
