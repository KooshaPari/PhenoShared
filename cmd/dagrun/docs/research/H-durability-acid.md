# H — Durability and ACID properties of the dagrun store

Status: measured against the tree as of this writing. Every claim below cites a file, a
test, or a measurement. Anything not confirmed in this session is marked **UNVERIFIED**.

Measured facts used throughout (from the 500-node claim-loop runs and the state document):

- One JSON document per run; an OS file lock (`flock`); atomic temp-file + rename.
- Leases with an epoch fence; a node is done only when its artifacts verify on disk.
- Claim loop: 66.3 node-ops/sec at 1 worker, 65.0 at 8, 63.9 at 32. Flat.
- `state.json` at 500 nodes = 88.4 KiB. Every transition rewrites the whole document.
- No daemon, no database, no broker.
- Lease TTL default 2m (`main.go:179`, `internal/workspace/exec.go:101-102`), heartbeat at
  `lease/3` (~40s) with `durable=false` (`internal/run/exec.go:252-255`, `internal/store/lease.go:190`).

---

## 1. What dagrun actually guarantees today

The store is `internal/store/store.go`: "the only mutable state in dagrun: one JSON document per
run, guarded by an OS file lock, written atomically." That sentence is accurate and it is narrower
than "ACID transaction" — it is a guarantee about *one document write*, not about one unit of work.

### Atomicity — yes, per document write; no, per unit of work

`writeState` (`store.go:179-232`) marshals the whole document, writes it to `state.json.tmp`,
`fsync`s only if `durable`, closes, then `os.Rename`s over `state.json`. Rename within one
directory is atomic on POSIX, so a reader or a restart sees either the previous document or the new
one, never a torn one. This is tested, not asserted: `TestTruncatedStateIsRefusedNotHalfRead`
(`crash_test.go`) cuts a real `state.json` in half and requires the store to refuse it as
`corrupt` rather than half-read it.

What is *not* atomic is the operation an operator cares about: "this node is done". That operation
is three separate effects in this order —

1. the harness process writes its artifacts to the filesystem,
2. `verify.PlanNode` returns `OK` over those artifacts (`internal/run/exec.go:169`),
3. `Finish`/`settleNode` persists `status=done` under the lock.

There is no transaction spanning 2 and 3. The residual window is the interval between "the
artifacts verify" and "the rename that records done has landed".

That window does **not** duplicate work, and this is the design's best move. A crash inside the
window leaves the node `running` with a live lease. The lease expires, `ResetExpired`
(`store.go:313-334`) returns it to `pending`, and the scheduler's `adopt` check
(`internal/run/run.go:205`) verifies the artifacts and `Force`s the node to `done` **without
spawning anything** (`run.go:514-562`, trace event `node.adopt`). `adopt` is only reachable for
`status == pending` nodes (`run.go:181-183`), so it can never race a live lease, and a node that is
already `done` is refused by `Claim` (`lease.go:105-112`), which is exactly the once-only guarantee
`TestCompletedNodeIsAdoptedNotRecomputed` asserts.

The honest cost of the window is *latency*, not correctness: recovery waits for lease expiry, so up
to one TTL (2m default) is burned before the node is recognised as done.

### Consistency — invariants are enforced; state/artifact agreement is reconciled, not transactional

Enforced, each inside the same critical section as the write that depends on it:

- A run is defined by one plan. `Open` hashes the plan and refuses a different plan unless
  `--reset` (`store.go:104-118`).
- Schema version is persisted and a state written by a **newer** binary is refused with a sentinel
  error rather than half-read, because half-reading silently drops unknown fields and the next
  write would persist that loss (`schema.go:1-31`, `store.go:158-162`). Missing version means 1.
  Migrations must be ordered and contiguous; a gap is an error, not a skip (`schema.go:49-79`).
- Dependency order (`DepsDone`), attempt budget (`plan.EffectiveAttempts`), and both concurrency
  caps (`capBlocked`) are evaluated under the same lock as the claim, so there is no TOCTOU between
  "count the running nodes" and "take the node" (`lease.go:97-179`).
- Status transitions other than `Force` are compare-and-set on `owner`+`epoch` and fail closed:
  a stale owner writes nothing and gets `false` (`lease.go:180-267`).

Not enforced, by design: agreement between `state.json` and the artifacts. Consistency runs in one
direction. Pending-but-artifacts-exist is healed by `adopt`. Done-but-artifacts-missing is **not**
healed: `Claim` refuses a `done` node, the scheduler only adopts `pending` nodes, so a node whose
artifacts were deleted out of band will never re-run. The operator-visible detectors are
`dagrun node check` (`cmd_node.go:144-175`, reports `broken` vs `adoptable`) and `--reset`. That
asymmetry is real and should be stated as such rather than called "eventual consistency".

### Isolation — effectively serializable, by serialising everything

Every mutation takes one exclusive advisory lock on `<run>/lock` for the whole read-modify-write
(`withState`, `store.go:242-266`), and `lockExclusive` is a blocking `LOCK_EX`
(`lock_unix.go:11-14`). One writer at a time per run, so no interleaving anomaly is possible: this
is the strongest isolation level, obtained by giving up write concurrency entirely. The isolation
unit is the run directory; two runs in different directories share nothing mutable.

Two consequences are worth naming because they are not obvious:

- **Readers take the write lock and they write.** `Snapshot` calls `With`, which calls
  `writeState`, so `dagrun status` rewrites `state.json` and bumps `UpdatedAt`. A polling monitor
  is a writer, and `UpdatedAt` is therefore not evidence that work happened.
- **There is no lock timeout.** A holder that stalls (SIGSTOP, a hung `fsync` on a failing disk,
  a machine suspended mid-critical-section) blocks every other dagrun process on that run
  indefinitely, with no diagnostic. The kernel releases the lock if the process *dies*; it does
  nothing if the process merely stops.

### Durability — crash-consistent for process death; not power-loss durable

`writeState` fsyncs the temp file's **data** before the rename, but deliberately does **not** fsync
the parent directory:

> "The rename is atomic. We deliberately do not fsync the directory: that doubles the syscall cost
> for a guarantee the artifact-based recovery path already provides (a lost transition means the
> node runs again and is adopted)." — `store.go:206-209`

Heartbeats skip the fsync entirely (`durable=false`, `lease.go:190`), which is sound: a lost
heartbeat only shortens a lease.

What `crash_test.go` proves is **process**-kill safety, not power-loss durability.
`TestKilledClaimantsLeaveExactlyOneClaim` SIGKILLs 6 contenders mid-claim and requires that at most
one claim survives, that a surviving claim carries an owner and a non-zero epoch, and that the
store is still writable after the kills. Under SIGKILL the kernel page cache still holds the
written bytes and completes the rename, so this test cannot distinguish a durable write from an
unflushed one. After a **power cut**, an unsynced directory entry may not be there: the tree falls
back to the pre-rename `state.json`, which is a coherent older document, so the loss is a lost
transition rather than corruption.

The sharpest edge is that the two halves of "node done" are *not ordered* against each other.
dagrun fsyncs neither the artifact directory (the harness owns that) nor the state directory. If
the state's file data lands and the artifact's data does not, the result is `status=done` over a
truncated artifact, and nothing re-runs it, because `done` is terminal. That is the one failure
mode in this design that is not self-healing.

### Summary line

Atomic per document, consistent by invariant and one-directional reconciliation, serialized to the
point of losing reader concurrency, crash-safe against process death, and *recoverable* rather than
durable against power loss — with one non-self-healing case at the state/artifact ordering boundary.

## 2. Where the design breaks

"Breaks" means a correctness or availability failure. "Slower" means it still works. The measured
claim-loop flatline at ~65 ops/s across 1/8/32 workers is evidence about the **lock**: adding
workers does not help and does not hurt, so contention is not the limit. Extrapolated state sizes
below are arithmetic from the measured 88.4 KiB at 500 nodes and are labelled as extrapolation.

### Breaks

| # | Failure | Mechanism | Threshold at which it bites |
|---|---|---|---|
| B1 | Power loss can publish `done` over an incomplete artifact | state file data is fsynced, artifact data and the state *directory entry* are not; no ordering between them (`store.go:206-209`) | any power cut / kernel panic that loses page-cache writes for one of the two; not reachable by SIGKILL |
| B2 | `done` is terminal, so a node that stops verifying never re-runs | `Claim` refuses terminal states (`lease.go:105-112`); `adopt` only sees `pending` (`run.go:181-183`) | artifact deletion, volume remount, a `git checkout` in the worktree, or B1 |
| B3 | Two workers run one node at once | lease TTL 2m with no heartbeat landing (SIGSTOP, laptop sleep, ENOSPC on the lock dir, a stuck flock holder). Epoch bumps, the loser's `Finish`/`RecordUsage` is discarded fail-closed (`lease.go:180-267`) | heartbeat failure for one TTL, i.e. ~2m of scheduled heartbeats not landing — not merely a node longer than 2m |
| B4 | The whole run stalls with no timeout | blocking `LOCK_EX` with no deadline; a holder that stalls rather than dies never releases | one stuck holder on that run directory |
| B5 | Mutual exclusion silently does not hold | `flock` is advisory and, on NFS/SMB/some FUSE mounts, may be local-only or unimplemented; nothing detects it | run directory on a network filesystem or a volume where flock is not shared |
| B6 | Downgrade loses all progress | refuse-newer is fail-closed and there is no down-migration (`schema.go:49-79`) | rolling back a binary after any `SchemaVersion` bump, without `--reset` |
| B7 | "done" is not self-certifying | `Force` ignores owner and epoch and accepts a nil report (`lease.go:272-288`); driving agents use it | any actor with filesystem access to the run dir, including `dagrun done` |
| B8 | A reader is a writer | `Snapshot` → `With` → `writeState`; bumps `UpdatedAt` on every `dagrun status` | any monitoring loop; also invalidates `UpdatedAt` as a work signal |

### Gets slower (does not break)

| # | Cost | Mechanism | Where it starts to matter |
|---|---|---|---|
| S1 | Every transition rewrites the whole document | marshal + write + (fsync) of O(nodes) bytes, 2-3+ times per node (claim, heartbeat, usage, finish) | 500 nodes = 88.4 KiB measured; 5,000 nodes ≈ 880 KiB per transition by the same ratio (extrapolation, not measured). Write amplification, not correctness |
| S2 | Reader latency tracks document size | readers take the same exclusive lock and rewrite the file | `dagrun status` on a large run is a write, not a read |
| S3 | Recovery latency = up to one lease TTL | `ResetExpired` only reaps after expiry | 2m default per lost transition; worse with a longer `--lease` |
| S4 | Serialised critical section caps transition rate | ~65 ops/s flat, independent of workers | does not bind today: at 8-32 workers the node rate is far below 65 ops/s because each node is a harness call of seconds to minutes. It would bind if node work ever became sub-100ms |

The important calibration: **the lock is not the bottleneck and the flatline is not a problem
anyone will hit.** At 32 workers, 63.9 ops/s of state transitions against node wall times measured
in tens of seconds is three orders of magnitude of headroom. The interesting risks are B1-B5, which
are all about *one* transition being wrong or stuck, not about many transitions being slow.

## 3. Per-tool comparison

Citation key: **[W]** = confirmed on `https://www.sqlite.org/wal.html` in this session;
**[T]** = confirmed on `https://docs.temporal.io/temporal-service/persistence` in this session;
**[U]** = UNVERIFIED — not confirmed in this session (a fetch to `lancedb.github.io/lance/`
returned HTTP 404 and the fetch budget of three was then spent). Unverified rows state what is
well-established prior knowledge and nothing more; no version numbers are asserted anywhere in this
table, because none were checked.

| Tool | What it is | Durability guarantee it adds (over dagrun today) | Operational cost | The dagrun scenario where it would be the right call |
|---|---|---|---|---|
| **Temporal** | Durable-execution engine: workflow code plus a server that persists an event history and replays it **[T]** | Its only required dependency is a persistence database, which stores tasks, workflow mutable state, an append-only history, namespace metadata and visibility data **[T]**. That buys event-sourced replay: a worker can die and the workflow continues from history rather than from a re-verifiable artifact | A server process plus a supported database. Production databases listed as tested: Cassandra 3.11/4.0/5.0.4+, PostgreSQL 13.18-16.6, MySQL 5.7/8.0; SQLite is supported but "meant only for development and testing, not production usage" **[T]**. Elasticsearch recommended for production visibility **[T]**. Server licence UNVERIFIED | Only if a dagrun node stops being a harness invocation and becomes a deterministic multi-step program needing timers, signals or replay across host loss. For a node whose truth is "the artifact exists", replay adds nothing |
| **Hatchet** | Workflow/task orchestrator with a queueing engine and a database-backed task store **[U]** | Durable queued dispatch and retries off a real database, i.e. at-least-once task delivery with server-side retry bookkeeping **[U]** | A long-running engine service plus a relational database; container/Helm deploy **[U]**. Licence UNVERIFIED | If dagrun had to dispatch nodes to machines that do not share a filesystem. That is a different product than a CLI whose lock lives in the run directory |
| **Prefect** | Python workflow orchestration with a server/Cloud API, agents, and server-side flow/task state **[U]** | Centralised run history and retry/scheduling state held by a server rather than by a file, so the client can be stateless **[U]** | A Prefect server or a Cloud account, a database, and a Python runtime **[U]**. Licence and current version UNVERIFIED | Only if dagrun were written in Python and orchestrating Python flows. A Go binary driving argv harnesses gains nothing and inherits a Python service |
| **SQLite (WAL)** | Embedded SQL database, WAL journal mode, no daemon **[W]** | Real page-level atomic commit: a COMMIT is a commit record appended to the WAL, and checkpointing moves it back to the database file **[W]**. Readers do not block writers and writers do not block readers **[W]**, which dagrun cannot do today (B8). Write cost is proportional to changed pages, not to node count, replacing S1/S2. `PRAGMA synchronous=FULL` syncs the WAL on every commit; `NORMAL` omits that sync and accepts a power-loss durability window **[W]** — the same trade dagrun makes today, but selectable per transaction rather than hard-wired | A C library and three files (`db`, `-wal`, `-shm`), no daemon, no licence fee (SQLite is public domain; the licence text itself UNVERIFIED in this session). Same host only: WAL requires shared memory and "does not work over a network filesystem" **[W]** — exactly the constraint that already breaks dagrun's `flock` (B5). A read-only WAL database needs its `-shm`/`-wal` present or directory write permission **[W]**, so "just mount it read-only" is not free | The first and only storage upgrade worth planning: a run whose state document outgrows a few MiB, or a run that needs a multi-entity invariant (a shared budget row plus node rows) committed atomically. It does not remove B1 (artifact-vs-state ordering) and does not remove B3 (a lease is still a lease) |
| **Lance** | Columnar, Arrow-based dataset format aimed at ML/vector data, with versioned dataset metadata **[U]** | Versioned dataset commits with atomic manifest updates, plus random access and vector search at scale — a guarantee about *large analytic/embedding* data, not about tiny hot row updates **[U]** | A Rust crate and a format-versioning story; no daemon. Best value at GB scale, not KiB scale **[U]** | Storing the *artifact index* for a portfolio of runs (embeddings, per-attempt telemetry over thousands of runs) as a read-side analytics store. Never for one run's 88.4 KiB live state |
| **DuckDB** | Embedded columnar OLAP engine, in-process, analytical SQL **[U]** | ACID transactions inside one process and very fast analytic scans over Parquet/JSON; typically one writer process per database file **[U]** | A C++ library, no daemon, no server. One writer at a time, so it reproduces dagrun's single-writer property at a much larger granularity **[U]**. Licence MIT per project convention — UNVERIFIED | `dagrun stats` / trace reporting across many runs, where columnar scans win. Not the state store: the workload is 1-row compare-and-set, the opposite of a columnar scan |
| **Redis Streams** | In-memory data structure server with an append-only stream log and consumer groups (PEL + `XACK`/`XAUTOCLAIM`) **[U]** | At-least-once delivery to a consumer group with explicit ack and reclaim of orphaned pending entries. Durability comes from AOF/RDB configuration, and the AOF fsync policy sets the power-loss window **[U]** | A `redis-server` daemon in the run path, memory sizing, and a persistence configuration that must be reasoned about separately from dagrun's own settings **[U]**. Licence UNVERIFIED (BSD-family per project convention) | Cross-host node dispatch with a lease-like reclaim path, already solved. For a local CLI it converts "no daemon" into "always a daemon" |
| **NATS JetStream** | Persistent, replicated messaging plus KV/object store on top of NATS, with acks and dedupe **[U]** | File-backed at-least-once delivery with a replication factor that survives loss of a minority of servers, plus message-id dedupe windows **[U]** | A `nats-server` process, and a cluster for the replication guarantee to mean anything. Always a daemon, always a port, always a lifecycle **[U]**. Licence UNVERIFIED | Multi-host dagrun where workers cannot share a filesystem but must share dispatch state. Explicitly *not* a fit for the single-machine case |
| **Neo4j** | Property-graph database with Cypher and ACID transactions **[U]** | Transactional graph storage with indexes and traversals: durable, queried relationships rather than a document you parse **[U]** | A JVM server, heap tuning, a licence decision (Community vs commercial — UNVERIFIED which terms apply now), and a cluster for HA **[U]** | Querying the *plan graph* across a portfolio ("which node blocks which across all runs"). The live state of one run is a small map, not a graph traversal problem |

Reading the table against section 2: **not one row fixes B1.** No store can order a filesystem
write performed by a third-party harness against a database commit in another subsystem. The
storage engine is not where the interesting risk lives; B1 is an ordering problem, B2 is a policy
problem (`done` is terminal), B3 is a lease-tuning problem, and B4/B5 are `flock` properties that
SQLite shares (same-host-only, no network filesystem support **[W]**).

## 4. Recommendation

Ranked by benefit per unit of risk. Each entry carries a trigger an operator could actually observe,
because an untriggered recommendation is a preference, not a recommendation.

**R0 — Change nothing about the storage engine. (Recommended.)**
Evidence: transitions are flat at 66.3 / 65.0 / 63.9 ops/sec across 1 / 8 / 32 workers, and at 32
workers the observed node rate is far below that because every node is a harness call. The store is
not the bottleneck by roughly three orders of magnitude, and no row in section 3 addresses the
failures that actually matter. Changing it now would pay a real migration cost for no measured
benefit.
*Trigger to revisit:* any one of — `state.json` exceeds 4 MiB (by the measured 88.4 KiB/500-node
ratio, about 20k nodes); OR p95 state-transition latency exceeds 5 ms; OR a run's wall time is
dominated by state writes in a profile.

**R1 — Bound the lock wait, and name the holder.**
A blocking `LOCK_EX` with no deadline is the only defect here that can silently stop a whole run
(B4). Acquire with a deadline (e.g. `LOCK_EX|LOCK_NB` in a poll loop), and on timeout report the
run directory and the holder's pid/start time so the operator can act.
*Trigger:* a dagrun invocation that produces no output for >30 s and has to be killed by hand — one
observation is enough.

**R2 — Make `Snapshot` not a writer.**
A read that rewrites the document and bumps `UpdatedAt` (B8) breaks the most basic monitoring
assumption and puts a monitor on the write path. Rename is atomic, so a read-only open of
`state.json` with no lock at all is coherent; keep the exclusive lock for mutations.
*Trigger:* `UpdatedAt` advancing while no node transitions, or any poll loop added to a dashboard.

**R3 — `fsync` the state directory on durable writes.**
One syscall closes the "lost transition" half of B1 and makes the durability claim match the word
`durable`. It does not close the artifact-vs-state ordering half, and should not be sold as doing
so.
*Trigger:* runs executed on a host without a UPS, or any incident where a `done` node's artifacts
are incomplete after a power event.

**R4 — Record artifact identity so `done` can be re-validated.**
Store the verified artifacts' hashes/mtimes in the node record at `Finish` time; then
`dagrun node check` can distinguish "done and still true" from "done but the artifact changed"
and the operator gets a decision point instead of B2 being invisible.
*Trigger:* `dagrun node check` reporting `broken > 0` on any run, or a worktree being
`git checkout`-ed while a run is still live.

**R5 — Move the state to SQLite in WAL mode.**
The correct engine change if R0's trigger fires: page-level writes instead of whole-document
rewrites, reader/writer concurrency, and real multi-row atomicity, with no daemon and no licence
decision **[W]**. Accept the same limitation dagrun already has: single host, no network filesystem
**[W]**. Keep `synchronous=FULL` for terminal transitions and `NORMAL` for heartbeats, which is
today's `durable` flag expressed in the engine.
*Trigger:* R0's trigger, i.e. >4 MiB state, p95 transition >5 ms, or a genuine multi-entity
invariant that must commit atomically.

**R6 — Adopt a server-side engine (Temporal / Hatchet / NATS JetStream / Redis Streams).**
*Trigger:* two workers on **different machines** must drive the same run — observed, not
anticipated. Until then these convert a dependency-free binary into an operated service and buy
nothing the artifact check does not already buy.

Ordering rationale: R1-R4 are local, testable, and fix the failures that bite; R5 is the storage
change worth planning for a threshold nobody has reached; R6 is a different product surface.

### Note on the ACID claim in the README

If the README or DESIGN says "ACID", the precise version of that claim is: **atomic and
serializable per document write, consistent by enforced invariant, crash-consistent against process
death, and recoverable rather than durable against power loss.** Anything stronger needs R3 plus an
artifact-durability story that dagrun cannot supply alone, because the harness owns the artifacts.

## 5. What NOT to adopt, and why

Rejected outright, regardless of section 3 detail:

| Rejected | One-line reason |
|---|---|
| A daemon or broker between the CLI and the state | The whole premise is that every dagrun command is short-lived and holds the lock for microseconds; a resident process reintroduces the lifecycle, upgrade, and restart problems the file store does not have. |
| A database (Postgres/MySQL) as the run store | It buys transactions the design does not need (one document, one writer) and costs a service the operator must run, back up, and version. |
| SQLite as a *replacement* store | It is the strongest alternative and is the right call at a threshold (see section 4), but adopting it today would trade a zero-dependency binary for a schema, migrations, and a writer-contention model to serve ~65 transitions/sec. |
| Vector/graph/columnar formats as the state store | Lance, DuckDB and Neo4j are analytic and relational/vector models; a run is a tiny, hot, row-shaped compare-and-set workload, which is the opposite shape. |
| Ethical or epistemic: an at-least-once log as the source of truth | A log gives at-least-once delivery, not "one worker did this once". Exactly-once here comes from artifact verification plus `done` being terminal, not from the transport. |
| `fsync` on every heartbeat | Heartbeats are idempotent and losing one only shortens a lease; paying a sync per heartbeat would move the cost onto the hot path for no gain. |
| Making `Snapshot` a lock-free read | A torn read of a multi-field invariant (owner/epoch/lease/status) is worse than a slow read; the fix is a read-only fast path that takes a shared lock, not no lock. |
| A down-migration chain | Every migration so far is identity; inventing reversible migrations for a document nobody has had to downgrade adds a maintenance obligation with no demonstrated need. `--reset` is the honest answer. |
| Optimistic retry loops around the lock | With a blocking `LOCK_EX` and microsecond critical sections, retry loops add latency and hide B4; the missing thing is a *timeout with a diagnostic*, not a retry. |
