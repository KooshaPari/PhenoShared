# Methodologies for a DAG-based, artifact-gated execution substrate

Scope: the technique families that exist in the field for durable DAG execution
where a node's completion is decided by artifacts rather than by an agent's
claim. Each entry gives the canonical name, the problem it solves, and a verdict
on whether `cmd/dagrun` embodies it, with the file that proves the verdict.

Every verdict below was derived by reading the module at `cmd/dagrun`
(i.e. `cmd_*.go` plus `internal/*`), not by reading its roadmap.

---

## 1. Workflow-as-code

The workflow is a declarative document held under version control, not an
imperative program and not rows in a scheduler's database. Every engine in this
space (Temporal, Argo Workflows, Airflow, Dagster, Flyte, Prefect) treats the
workflow definition as an artifact with a diffable history, so a change to the
pipeline is reviewable like any other change. It solves the problem of
irreproducible scheduling: the definition of the work and the record of the work
can be compared.

**Verdict: IMPLEMENTED.** The plan is a YAML document that stays the source of
truth for the run. `internal/plan/plan.go` defines the schema (`Plan`, `Node`,
`Artifact`); `internal/plan/dagschema.go:383-427` additionally imports a foreign
DagSchema and rejects it if it is cyclic. `internal/plan/cvp.go:1-20` states the
doctrine explicitly ("The plan file stays the source of truth") when it declines
to widen the plan schema for the checkpoint key. `internal/plan/validate.go`
is the static gate on that document, and `internal/plan/draft.go` /
`internal/plan/templates.go` author it.

## 2. Artifact-gated promotion

A node does not advance because a process exited or an agent said it succeeded;
it advances because the outputs it declared are present and satisfy a predicate.
This is the "contract-based promotion" pattern used by CI gates and by build
systems with declared outputs (Bazel's declared outputs, Argo's `outputs`
artifacts, Tekton `results`). It solves the problem of unverifiable success: the
completion signal is a fact about the filesystem, not a report.

**Verdict: IMPLEMENTED.** This is dagrun's one invariant. `DESIGN.md` states it
as "A node is `done` if and only if every artifact it declared exists and
satisfies its predicate, and its `check`, if any, exits 0."
`internal/verify/verify.go` implements it: `Node` and `PlanNode` produce a
`Report`; `Satisfied` is the artifacts-only pre-filter; `checkArtifact`
(`verify.go:134`) enforces existence, glob cardinality (`MinCount`,
`too_many_matches`), size (`MinBytes`), `MustContain`, `MustMatch`,
`AllowEmpty`, and runs the node's `check` via `runCheck` (`verify.go:293`).
`internal/verify/kinds.go` adds per-kind contracts (`SPEC` requires a
`Requirement` statement, etc.) so a node of a given kind cannot satisfy its
contract with prose of the wrong shape.

## 3. Idempotent node execution

Re-executing a node must not duplicate its effect. The standard formulation is
"the operation is safe to repeat" and it is what makes retries and resumes
possible at all. Engines implement it either by making the work itself
idempotent (Temporal activities with idempotency keys) or by adopting
already-satisfied work instead of redoing it (build systems: Bazel's
action cache, Make's timestamp/phony rules).

**Verdict: IMPLEMENTED.** dagrun uses adoption, not re-run. `internal/run/run.go:512`
(`adopt`) accepts a node whose artifacts already satisfy the contract:
`run.go:533` calls `verify.Satisfied`, and `run.go:565` records
`"adopted: artifacts already satisfy the contract"`. `run.go:528` documents the
exactly-once property of adoption ("the check executes exactly once per
adoption"). Dynamic fan-out expansion is idempotent per parent
(`run.go:156`), so several executors may expand the same parent without
producing duplicate children. The behaviour is pinned by tests:
`internal/store/crash_test.go:156` `TestCompletedNodeIsAdoptedNotRecomputed`.

## 4. At-least-once vs exactly-once execution semantics

The field distinguishes "the work is attempted at least once" (safe, requires
idempotence downstream) from "the work happens exactly once" (requires a
distributed commit or a transactional side effect). Every durable engine has to
state which one it provides, because the answer determines what the caller must
make safe.

**Verdict: PARTIAL.** The *scheduler* is at-most-one-owner and
non-duplicating: a claim is a compare-and-set on owner+epoch
(`internal/store/lease.go`), and `internal/store/crash_test.go:22`
`TestKilledClaimantsLeaveExactlyOneClaim` proves that killed claimants leave
exactly one claim. Adoption (§3) makes a completed node non-recomputed on
re-run. What is *not* exactly-once is the child process's external side effect:
a node may have mutated the world and lost its lease before recording the
result, so its effect is at-least-once and the node's own work must still be
idempotent. dagrun does not attempt to compensate for that; the gap is closed
only by re-running a node whose artifacts are absent.

## 5. Saga / compensation

Long-lived distributed transactions are not rolled back; they are *compensated*:
each step declares an inverse action, and failure triggers the inverse actions
of the completed steps in reverse order (the saga pattern, Garcia-Molina &
Salem 1987; implemented in Temporal as saga/compensation, in AWS Step Functions
as Catch + compensating states). It solves the problem of partial completion in
a system with no distributed transaction.

**Verdict: ABSENT.** Grepped for `saga`, `compensat`, `rollback`, `undo` across
all non-test `*.go` in the module. The only hit is a comment
(`internal/plan/semantic.go:54`, describing that a migration's contract is its
ordered steps *and* its rollback) — a prose model of a migration node, not a
mechanism. `internal/run/failure.go` propagates failure by blocking dependent
nodes; it does not schedule inverses. There is no `compensate:` field on
`plan.Node` (`internal/plan/plan.go:66`).

## 6. Checkpoint-and-resume

Progress is durably recorded at a boundary so that an interrupted run continues
from that boundary rather than from the beginning. The checkpoint is the unit of
recovery in every durable execution system (Temporal's workflow history and
continue-as-new, Argo's per-node status, Airflow's task-instance state). It
solves the problem of a long run losing all work when one process dies.

**Verdict: IMPLEMENTED.** There are two layers. The coarse checkpoint is the CVP
gate: `internal/plan/cvp.go` defines the checkpoint as the last `GATE` node in
topological order (`CVPGate`, `cpv.go:25`) and answers "what next?" in terms of
the gate's ancestors rather than the whole tree. The recovery layer is
`internal/recover/recover.go` — `Report` (dry-run diagnosis of stuck nodes) and
`Reclaim` (the deliberate repair, which refuses a live lease) — surfaced as
`cmd_recover.go`, whose header states that a reclaim never resets the attempt
counter. `store.ResetExpired` (`internal/store/store.go:347`) clears expired
leases and emits the work back to the scheduler. `internal/store/crash_test.go`
pins the crash semantics.

## 7. Content-addressed artifact verification

Output is identified by the digest of its bytes rather than by its name or
timestamp, so equality is exact and a substituted or duplicated artifact is
detectable. This is the Nix/Bazel/Git model (and the in-toto attestation model),
and it is what makes caching and anti-substitution checks possible.

**Verdict: PARTIAL.** dagrun *computes* content addresses: `checkArtifact`
(`internal/verify/verify.go:134`) hashes each artifact with `sha256.Sum256` and
returns it on `ArtifactResult.SHA256`, and `internal/verify/antigaming.go:177-188`
uses the digests as an anti-gaming signal — a run where every artifact shares one
digest, or where the digest is not digest-shaped, is flagged. Digest and size are
carried into every export (`internal/export/export.go:203`,
`internal/tracera/tracera.go:184`). What is missing is *pinning*:
`plan.Artifact` (`internal/plan/plan.go:53-63`) has `Path`, `MinBytes`,
`MustContain`, `MustMatch`, `MinCount`, `AllowEmpty` — but no declared expected
`sha256`. So the digest is recorded and cross-checked against other digests of
the same run, not compared against an expected value in the contract.

## 8. Provenance capture

An execution record should answer *what produced this artifact, from what
inputs, by which agent and tool version*. Canonical forms are W3C PROV (entity /
activity / agent) and in-toto link metadata (materials, command, products,
byproducts). It solves the problem of an un-auditable result: knowing a file
exists is not knowing how it came to exist.

**Verdict: PARTIAL.** The run records a typed event stream: `internal/trace/trace.go`
defines `Event` with `TS`, `Run`, `Node`, `Worker`, `Event`, `Epoch`, `Attempt`,
`Exit`, `DurMS`, `Message`, `Attrs` — that is activity + agent + attempt, which
is the core of the PROV shape. Node-level attribution (path, sha256, bytes) is
exported alongside it (`export.go:203`, `export.go:299`). What is absent is the
*materials* half: the source revision and environment are not recorded in
`state.json` or in the trace. Grepped `rev-parse`, `HEAD`, `commit` across
`internal/run`, `internal/workspace`, `internal/trace`: the only hits are
worktree creation (`internal/run/worktree.go:46,55`) and a worktree diff scope
(`internal/run/exec.go:205`). No commit id is stored as run provenance, so an
exported artifact cannot be tied back to the tree it changed.

## 9. Claim-based work distribution

Workers take units of work by claiming them, and the claim is a
compare-and-set that expires. Ownership is held as a lease with a monotonically
increasing epoch (fencing token), so a worker whose lease expired cannot overwrite
its successor's result. This is the distributed-lock/fencing-token pattern
(Kleppmann's fencing tokens; lease-based ownership in Chubby and in every
lease-based queue). It solves the problem of two workers executing the same unit
and of a slow worker clobbering a fast one.

**Verdict: IMPLEMENTED.** `internal/store/lease.go:1-5` states the contract:
"Every mutating call is a compare-and-set against owner+epoch, so a worker whose
lease expired cannot write a result over its successor's." `internal/store/store.go`
carries `Epoch int64` and `LeaseUntil time.Time` on node state and exposes
`Claim`; `ResetExpired` (`store.go:347`) is the only path that returns an expired
lease to the pool. Deliberately, there is no stale-lock reaper: `DESIGN.md` D1
records that `flock` gives the crash property for free because the kernel drops
the lock when the process dies. The claim verbs are exercised through
`cmd_next.go` / `cmd_run.go` and the workspace runner (`internal/workspace/exec.go:144`,
"A node that has not been claimed yet is neither done nor failed").

## 10. Deterministic replay

Given the recorded decision inputs, the engine can re-derive the same schedule
and the same outcomes without re-running side effects. Temporal replays workflow
history deterministically against worker code; event-sourced systems replay a log
to rebuild state. It solves the problem of debugging and auditing a
non-repeatable execution, and it is the precondition for "re-run the decision,
not the work".

**Verdict: ABSENT.** Grepped `replay` across all non-test `*.go`: the only code
hit is `internal/plan/budget.go:172`, which notes that a substring fallback is
deterministic — unrelated to replay. There is no event-sourced journal:
`internal/trace` is an append-only *observation* log (it records what happened),
not a decision log that state is rebuilt from, and `state.json` is
last-writer-wins under `flock` (`internal/store/store.go:179`), not a fold over
events. The closest mechanism is drift detection: `State.PlanHash`
(`store.go:57`, computed at `store.go:97`, enforced at `store.go:105`) refuses to
open a run directory whose plan bytes changed. That detects divergence; it does
not replay a decision sequence.

## 11. Static plan validation (acyclicity and contract satisfiability)

A plan is checked before execution for properties that make execution
meaningless if violated: the dependency graph must be a DAG, and every node must
declare a verifiable contract. This is the plan-time half of "fail closed"
(comparable to a compiler's type check, and to Argo's and Airflow's DAG
validation on load). It solves the problem of discovering a structural defect
after hours of execution.

**Verdict: IMPLEMENTED.** `internal/plan/dagschema.go:383-427` performs a
topological check and rejects a cycle: `"DagSchema contains a cycle: %d of %d
nodes are orderable"`. `internal/plan/validate.go:76` enforces satisfiability of
the contract: `verifiable := len(n.Artifacts) > 0 || n.Check != ""` — a node with
no verifiable contract is rejected at plan time, which is the mechanism behind
`DESIGN.md`'s claim that "a node with no verifiable contract is rejected at plan
time". `internal/plan/overlap.go` and `internal/plan/semantic.go` add
cross-node coherence checks, and `cmd_lint.go` exposes the whole set.

## 12. Crash-safe durable state (atomic write, fsync, advisory lock)

State that is rewritten in place must survive a kill at any instruction. The
standard construction is write-to-temp, `fsync`, `rename`, plus an advisory lock
so concurrent writers serialize, plus a refusal to interpret a truncated record
as a half-state. It solves the problem of corrupted state after a crash, and it
is the alternative to a database for small state.

**Verdict: IMPLEMENTED.** `internal/store/store.go:179` (`writeState`, durable
path) does temp+rename; `internal/store/lock_unix.go` / `lock_windows.go` supply
the platform lock; `withState` (`store.go:242`) bounds the critical section.
`DESIGN.md` D1 records the decision and its rejection of SQLite/bbolt. The
truncation property is pinned by `internal/store/crash_test.go:120`
`TestTruncatedStateIsRefusedNotHalfRead`, and the killed-claimant property by
`crash_test.go:22`.

---

## The three methods dagrun most needs next

All three are drawn from the ABSENT and PARTIAL rows above.

### 1. Deterministic replay / decision journal (currently ABSENT, §10)

Reason: §10 is the only absent capability that blocks *auditing* rather than
*tolerance*. Today a finished run can say what happened (`trace.Event`) but not
re-derive why the scheduler chose what it chose, so a disputed schedule cannot be
reconstructed and a "would the new plan have produced the same order?" question
has to be answered by re-running real work. It also strengthens §6: a replayable
journal makes resume a fold rather than a lease sweep.

Where it lands: a decision journal beside the observation shards — extend
`internal/trace` (currently write-only `Emit`, plus `merge`) into an
append-and-fold API, and have `internal/store` fold the journal on `Open`
(`internal/store/store.go:87`) so `state.json` becomes a materialised view rather
than the only record. `cmd_timeline.go` and `cmd_replan.go` are the natural
readers.

### 2. Saga / compensation (currently ABSENT, §5)

Reason: `internal/run/failure.go` propagates failure *forward* (dependents are
blocked) and stops there. A node that already mutated a repository, a remote, or
an external system leaves that mutation in place when a sibling later fails.
That is the exact gap the saga pattern exists to close, and it is the one failure
mode a purely artifact-gated engine cannot verify its way out of: the artifacts
of the rolled-forward node are still valid, so adoption will keep them.

Where it lands: a `compensate:` field on `plan.Node`
(`internal/plan/plan.go:66`) validated by `internal/plan/validate.go`, executed
in reverse topological order by `internal/run/failure.go` when a run fails, with
each compensation itself verified by `internal/verify` (a compensation is a node
with a contract, so it is adoptable and traceable like any other).

### 3. Content-pinned artifact verification (currently PARTIAL, §7)

Reason: the digest is already computed and already exported, but it is not part
of the contract, so it cannot refuse a substituted artifact. Because dagrun's
whole guarantee is "artifacts, not claims", the pin is the difference between
"the file exists and has the shape I asked for" and "the file is the file I
expected". It is also cheap: the hash is already in hand at
`internal/verify/verify.go:190`.

Where it lands: add `sha256` to `plan.Artifact`
(`internal/plan/plan.go:53-63`), populate it from a successful run
(`cmdDone` in `cmd_node.go` / `store`), and compare it in `checkArtifact` after the existing
`sha256.Sum256` call, with a distinct code (e.g. `digest_mismatch`) so the
existing `Report` shape carries it without change.

---

Status: draft, authored 2026-11-12 from module state at commit 128b9f1982a96fe9e90f8c0130176d84b862a52a
