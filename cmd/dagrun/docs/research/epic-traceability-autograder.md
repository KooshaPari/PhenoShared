# Epic direction: traceability as an automatic, machine-graded property

Module: `cmd/dagrun` (module `github.com/KooshaPari/dagrun`, go 1.25.0)
Scope of this document: the CLI surface and the persisted run record. Nothing here is implemented.

---

## The problem, grounded in the current module

dagrun already records a great deal. The question this epic answers is narrower: **can the record
be graded, on demand, without re-running anything, and without a human reading prose?**

### What is recorded today

| Fact | Where it is written | Shape |
|---|---|---|
| Installed plan | `openRun` reads `<dir>/run.yaml` (`main.go:269-281`) | plan YAML |
| Run state | `<dir>/state.json` (`internal/store/store.go:125`, `statePath`) | `store.State`, `SchemaVersion = 1` (`internal/store/schema.go:33`) |
| Per-node outcome | `store.NodeState` (`internal/store/store.go:31-51`) | `Status`, `Attempts`, `Epoch`, `StartedAt`, `FinishedAt`, `ExitCode`, `Worktree`, `Branch`, `DurationMS`, `LastError`, `Verify *verify.Report` |
| Per-artifact verdict | `verify.Report` (`internal/verify/verify.go:24-56`) | `ArtifactResult{Path, OK, Code, Detail, Files, Bytes, SHA256}` plus `Check{Command, OK, ExitCode, Output, DurationMS}` |
| Execution record | append-only per-worker JSONL shards, `internal/trace/trace.go:24-39` | `trace.Event{TS, Run, Node, Worker, Event, Epoch, Attempt, Exit, DurMS, Message, Attrs}` |
| Published documents | `cmd_report.go` (`cmdCritique`, `cmdReview`) -> `internal/report` | CRITIQUE.md / REVIEW.md prose |
| Export document | `cmd_view.go:302` `cmdExport` -> `internal/export/export.go:297-303` | tracera doc carrying per-artifact `path`, `bytes`, `sha256` (`export.go:203`) |

`verify.Report` is produced at four online call sites and nowhere else: `cmd_node.go:69` (`dagrun
done`), `cmd_node.go:150` (`dagrun validate`), `internal/run/run.go:536` and
`internal/run/exec.go:86,169` (the scheduler), plus the MCP surface `internal/mcp/tools.go:272,372,394`.
The verify package states its own contract in `internal/verify/verify.go:3-6`:

> a node is done only when every declared artifact satisfies its predicate and the optional check
> command exits 0. Nothing here asks a model, reads intent, or trusts a claim.

### What it cannot answer automatically

1. **No run-wide re-grade.** `dagrun explain NODE` (`cmd_explain.go:113`) does re-verify, and it
   already knows the right language: "the node is recorded done but its artifacts no longer verify"
   (`cmd_explain.go:155`). But it grades **one node**, interactively, and its exit code is a
   statement about that node (`cmd_explain.go:20`). There is no command that grades the whole run
   and returns one exit code. `dagrun status` (`cmd_view.go:158`), `dagrun query`
   (`internal/query/query.go:230-242`) and `dagrun review` (`internal/report/report.go:212`) all
   render the **persisted** verdict. A persisted verdict is a claim about the past.
2. **Freshness is not represented.** `ArtifactResult` carries `Bytes` and `SHA256` but no mtime, and
   `internal/verify/verify.go:192` hashes the file at check time only. So the record cannot say
   whether the file present now is the file that was hashed. The digest is there; the comparison is
   nobody's job.
3. **Producer binding is absent.** `NodeState.StartedAt`/`FinishedAt` exist and `export.go:290-294`
   publishes them, but no code compares an artifact's mtime to the window of the attempt that claims
   it. "Produced by the run that claims it" is currently an assumption, not a checked property.
4. **Declared digests do not exist in the plan schema.** `plan.Artifact`
   (`internal/plan/plan.go:53-63`) has `Path`, `MinBytes`, `MustContain`, `MustMatch`, `MinCount`,
   `AllowEmpty` - and no digest field. So "match its declared digest" can only mean **match the
   digest recorded at verification time**. That is a real check but a weaker claim, and it must be
   named as such rather than described as content pinning.
5. **Override is invisible at the run level.** `dagrun done NODE --force` (`cmd_node.go:56-57`)
   persists `Status = done` with `Verify.OK = false` and the reason `"forced done by operator"`.
   `status` renders it identically to a verified node; only a reader who opens `state.json` can tell.
6. **The trace is not cross-checked against state.** State can claim a terminal outcome for an
   attempt that has no corresponding execution event in the trace shards.

---

## Epic statement

**Autograder**: one command that reads the persisted run record (`.dagrun/state.json`), the installed
plan (`run.yaml`) and the merged trace, then grades, from the filesystem **as it is now**, whether
every node recorded `done` still satisfies the contract it declared: each declared artifact exists,
satisfies its predicates, matches the digest recorded for it at verification time, and was last
modified inside the execution window of the attempt that claims it. It prints a machine-readable
grade per node and exits `0` (all graded claims hold), `1` (any claim is now false), or `2` (the record
could not be read). It is read-only: it never writes `state.json`, never writes the trace, and never
attests a node. Grading and attesting stay different verbs, because evidence must not be able to
promote itself into authority.

---

## Dependency order and critical path

Ordered by dependency. **Critical path: E1 -> E2 -> E3.** E4 and E5 are leaves off E1; E6 is a leaf
off E1.

---

## E1. `dagrun grade`: read-only run-wide re-grade (critical path, start here)

- **Outcome:** `dagrun grade [--dir DIR] [--json]` grades every node whose persisted status is `done`
  by calling `verify.PlanNode` afresh with the plan in view, compares the recomputed `SHA256` against
  the persisted `nodes[*].verify.artifacts[*].sha256`, and exits `1` if any recorded claim no longer
  holds.
- **Files:** new `cmd_grade.go`; one `case "grade":` in the `switch` at `main.go:38-120`; one line in
  `usage` (`main.go:124`). Reuses `openRun` (`main.go:269`) and `verify.PlanNode`.
- **Acceptance test** (deterministic: `--force` guarantees a recorded-done node whose verdict is
  `OK:false`, whatever the filesystem holds):
  ```bash
  cd cmd/dagrun && go build -o /tmp/dagrun-grade .
  T=$(mktemp -d ~/CodeProjects/temp/grade.XXXXXX); cd "$T"
  /tmp/dagrun-grade plan "$OLDPWD/examples/next-cvp/plan.yaml"
  NODE=$(/tmp/dagrun-grade query --select id --limit 1 --json | jq -r '.[0].id')
  /tmp/dagrun-grade done "$NODE" --force
  /tmp/dagrun-grade grade; echo "exit=$?"
  ```
  Expected observable: a line naming `$NODE` with grade `FORCED`/`DRIFT`, then `exit=1`. Against a
  freshly installed run with no done nodes, `grade` prints no graded rows and `exit=0`.
- **Risk:** duplicating verify logic. Mitigated by contract: `cmd_grade.go` may call
  `verify.PlanNode` and read `verify.Report` fields, and must not reimplement a single predicate. A
  duplicate would silently bypass the ReDoS caps in `internal/verify/limits.go:9-27`.

---

## E2. Freshness evidence: record the mtime that was hashed

- **Outcome:** `verify.ArtifactResult` gains `ModTime` (RFC3339, `omitempty`), populated in
  `checkArtifact` at hash time, so a grade can distinguish "this file" from "a file at this path".
- **Files:** `internal/verify/verify.go` (`ArtifactResult` struct at `:24-35`, `checkArtifact` at
  `:134`). Optional surfacing in `internal/export/export.go:203`.
- **Acceptance test:**
  ```bash
  cd cmd/dagrun && go test ./internal/verify -run ModTime -v
  ```
  Expected observable: `--- PASS: TestArtifactResultRecordsModTime`. Plus a live check that the field
  is populated and not zero: `/tmp/dagrun-grade grade --json | jq -r '.nodes[].artifacts[]?.mod_time'`
  prints non-empty RFC3339 values.
- **Risk:** `verify.Report` is embedded in `state.json`, and `internal/store/schema.go:7-18` warns
  exactly about older binaries dropping fields they do not know on rewrite. **Do not bump
  `SchemaVersion`.** Instead make the grader treat a missing `ModTime` as `UNKNOWN` freshness, so an
  older binary stripping the field degrades evidence to unknown rather than to a false pass.

---

## E3. Producer binding: artifact mtime inside the claiming attempt's window (critical path)

- **Outcome:** each graded artifact is classified `CURRENT` / `STALE` / `FOREIGN` by comparing
  `ModTime` to `NodeState.StartedAt`..`FinishedAt` (plus a tolerance flag), producing the strong form
  of "produced by the run that claims it".
- **Files:** new `internal/grade/grade.go` (so the CLI and MCP share one implementation, the same way
  `internal/query` is shared today); `cmd_grade.go` calls it.
- **Acceptance test:**
  ```bash
  # after attesting a node whose artifact path is P
  touch -t 200001010000 "$P"
  /tmp/dagrun-grade grade --json | jq -r '.nodes[] | select(.artifacts[]?.freshness=="STALE") | .node'
  ```
  Expected observable: prints that node id. Exit is `0` without `--strict` (freshness is a finding)
  and `1` with `--strict`.
- **Risk:** false `STALE` from clock skew, `git checkout` resetting mtimes on a branch worktree, and
  generators that preserve timestamps. That is why the default is a finding, not a failure, and why
  the tolerance is explicit.

---

## E4. Trace attestation: a done node must have an execution event for its attempt

- **Outcome:** for each node graded `done`, require a terminal event in the merged trace matching
  `Node` + `Attempt` + `Epoch`; otherwise grade `UNATTESTED`. Closes the gap where state claims an
  outcome the trace never saw.
- **Files:** `internal/grade/grade.go` (consumer), `internal/trace/trace.go` (existing read/merge
  surface only).
- **Acceptance test:**
  ```bash
  /tmp/dagrun-grade grade --json | jq -r '[.nodes[] | select(.proof=="UNATTESTED")] | length'
  ```
  Expected observable: `0` on a run produced by `dagrun run`; a hand-written `state.json` that marks
  a node done (no trace) yields `>=1` and the named node.
- **Risk:** `dagrun gc` (`cmd_house.go:82`) prunes trace shards, which would turn honest history into
  `UNATTESTED`. Treat a missing or pruned trace as `NO_EVIDENCE`, reported separately from a
  contradicting trace, and never as a pass.

---

## E5. Declared-digest plans: pin a digest in the plan, grade against the pin

- **Outcome:** `plan.Artifact` gains an optional `sha256:` field; plan validation rejects a malformed
  digest; the grader compares it to the actual content. This is the only way "match its declared
  digest" becomes a statement about content rather than about the record.
- **Files:** `internal/plan/plan.go` (`Artifact` at `:53-63`), plan validation, `internal/grade`.
- **Acceptance test:**
  ```bash
  cd cmd/dagrun && go test ./internal/plan -run Digest -v
  ```
  Expected observable: `--- PASS` for one valid pin and one test asserting a 63-character hex digest
  is rejected with a named error. Live: pin a wrong digest, `grade` names that artifact `DIGEST_MISMATCH`
  and exits `1`.
- **Risk:** a pinned digest makes legitimate regeneration a failure. Opt-in only, and `lint` should
  warn rather than error when a pin looks like it was copied from a previous run.

---

## E6. Surface the grade where the claim is read: `review` and MCP

- **Outcome:** `dagrun review` and the MCP tool set report the grade next to the persisted verdict, so
  a reader cannot see "done" without also seeing whether that claim currently holds. Includes the
  forced-done count.
- **Files:** `internal/report/report.go` (`Review` at `:200-235`), `internal/mcp/tools.go`,
  `cmd_report.go`.
- **Acceptance test:**
  ```bash
  /tmp/dagrun-grade review --json | jq -r '.review.grade.verdict'
  ```
  Expected observable: `current` / `drifted` / `unknown`, and on a run containing a forced node,
  `.review.grade.forced >= 1`.
- **Risk:** report output is consumed as prose by humans and as JSON by tooling; adding a section
  must not reorder or rename existing fields. Additive only.

---

## How the grader reports a verdict

The exit code is the run-wide statement; the per-node and per-artifact labels are what makes it
diagnosable. Both are fixed by the epics above, and neither may be reported as a pass when the input
was unreadable.

| Exit | Meaning |
|---|---|
| `0` | every graded claim holds |
| `1` | at least one recorded claim is now false |
| `2` | the record could not be read |

| Label | Meaning | Introduced by |
|---|---|---|
| `FORCED` | node is persisted `done` with `Verify.OK = false` (reason `"forced done by operator"`) | E1 |
| `DRIFT` | recomputed verdict no longer matches the persisted claim | E1 |
| `ModTime` missing -> `UNKNOWN` freshness | older binary stripped the additive field; degrades to unknown, never to a pass | E2 |
| `CURRENT` / `STALE` / `FOREIGN` | artifact mtime inside / outside / not attributable to the claiming attempt's window | E3 |
| `UNATTESTED` | node graded `done` with no matching terminal trace event | E4 |
| `NO_EVIDENCE` | trace missing or pruned by `dagrun gc`; reported separately from a contradicting trace | E4 |
| `DIGEST_MISMATCH` | content does not match the digest pinned in the plan | E5 |
| `current` / `drifted` / `unknown` | the `review` verdict next to the persisted one, plus the forced-done count | E6 |

---

## What must NOT be built (scope fence)

| Not built | Reason |
|---|---|
| A second verifier: any predicate, glob, regex or check-command logic inside the grader | `internal/verify` already owns this and enforces the attacker-input caps in `internal/verify/limits.go:9-27`. A parallel implementation drifts silently and loses the caps. The grader calls `verify.PlanNode` or it does not grade. |
| Anything that writes `state.json` or the trace | The record is what happened. Grading is a statement about now. A grader that writes makes the evidence mutable by a non-run process and breaks the append-only model in `internal/trace/trace.go:3-8`. |
| Auto-attestation: grade passes -> mark the node done | `dagrun done` is the attestation verb (`cmd_node.go:49`). Letting evidence promote itself to authority is the exact failure the `--force` reason string exists to make visible. |
| A daemon or filesystem watcher that invalidates state on change | Turns an on-demand computation into background mutation, and adds a second writer to the run directory. |
| Grading "does this satisfy the intent" with a model | `internal/verify/verify.go:3-6` states the opposite contract. Intent grading belongs to a different, clearly labelled surface, never to this exit code. |
| A `dagrun verify` command name | `verify` already names the package and the act at attestation time. A CLI verb of the same name is ambiguous between "verify now" and "re-read the last verdict". The name is `grade`. |
| Bumping `SchemaVersion` for E2's additive field | Additive `omitempty` evidence, regenerable, and an older binary stripping it must degrade to `UNKNOWN` rather than force a migration (`internal/store/schema.go:33-58`). |
| Treating missing evidence as passing | Every unreadable input is `UNKNOWN`/`NO_EVIDENCE` with its own exit contribution, never `PASS`. |

---

## The first 10-minute slice

**Change:** add `cmd_grade.go` with a single read-only pass - `openRun(dir)`, iterate `p.Sorted()`,
skip every node whose persisted `Status != done`, call
`verify.PlanNode(context.Background(), st.Root(), n, p)`, print `id  grade  detail`, set exit `1` if
any graded node returns `OK == false`, and also treat `ns.Status == done && ns.Verify != nil &&
!ns.Verify.OK` as a failure (`FORCED`). No digest comparison, no freshness, no JSON, no new package.
Plus the one `case "grade":` in `main.go`. Roughly 60 lines, no new dependency.

**Why this is the smallest starting point:** it needs no schema change, no new package, and no change
to the record. It converts an existing per-node capability (`cmd_explain.go:113`) into a run-wide exit
code, which is the whole idea in miniature.

**Exact proof:**

```bash
cd cmd/dagrun && go build -o /tmp/dagrun-grade .
T=$(mktemp -d ~/CodeProjects/temp/grade.XXXXXX) && cd "$T"
/tmp/dagrun-grade plan "$OLDPWD/examples/next-cvp/plan.yaml"
NODE=$(/tmp/dagrun-grade query --select id --limit 1 --json | jq -r '.[0].id')
/tmp/dagrun-grade grade; echo "exit=$?"
```

Expected: no graded rows (nothing is `done` yet), `exit=0`. Then:

```bash
/tmp/dagrun-grade done "$NODE" --force
/tmp/dagrun-grade grade; echo "exit=$?"
```

Expected: one line `<node>  FORCED  forced done by operator`, `exit=1`. That pair of observables
proves the grader reads the persisted record, re-grades it, and returns a machine-usable verdict -
which is the whole epic, in one command.

---

Status: draft, authored 2026-11-12T12:25Z from module state at commit 128b9f1982a96fe9e90f8c0130176d84b862a52a
