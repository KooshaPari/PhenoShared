# dagrun — design

Status: implemented. `README.md` is the user-facing reference;
`docs/research.md` records what the research changed; `docs/harness-notes.md` is
the observed harness contract. This file is the decision record.

## Problem

Agents need a fast, reliable way to turn an intent into a work DAG, execute it,
and prove each unit happened. `agileplus` and `tracera` will own that eventually.
Today they are not usable as drivers. `dagrun` is the small thing that works now
and exports into both.

## The one invariant

> A node is `done` if and only if every artifact it declared exists and satisfies
> its predicate, and its `check`, if any, exits 0.

Everything else is scheduling. There is no quality judgement, no intent
inference, no model in the control loop. Consequence: an agent cannot claim
success, and a node with no verifiable contract is rejected at plan time.

## Architectural decisions

### D1. On-disk state: JSON + `flock`, not a database

One `state.json` per run, rewritten under an exclusive `flock` with
`tmp` + `fsync` + `rename`.

Rejected `modernc.org/sqlite`: it would be correct (research measured 6 processes
× 25 transactions clean), but v1.61.0 needs Go ≥ 1.26 and the binary grows from
~3 MiB to ~9.6 MiB. Rejected bbolt/Badger: single-process only. Rejected
cgo SQLite: breaks a trivially installable binary.

What is kept from the SQLite design is its *shape*: compare-and-set claim, lease,
epoch fencing, and "my write affected nothing, so I lost ownership". `flock`
provides the same crash property — the kernel drops the lock when the process
dies — so there is no stale-lock reaper anywhere in the codebase.

Bounded by construction: the critical section is microseconds, and it is never
held across a child process.

### D2. Adoption instead of resume flags

If the artifacts verify, the node is done. No separate "resumed" or "already
ran" state to get out of sync. `dagrun run` therefore resumes by simply being
run again, and re-running never duplicates work.

### D3. Trace shards per worker

`.dagrun/trace/<worker>.jsonl`, one JSON object per line, `O_APPEND`. No two
processes write the same file, so there is nothing to contend on. `dagrun trace`
merges by timestamp.

There is no second trace system. The node event *is* the trace.

### D4. Harness as argv, not SDK

`harness.Adapter` is a name, a binary, and an argv builder. `auto` prefers the
harness that launched this process (`JCODE_*` / `KCODE_*` / `CODEX_HOME` /
`FORGE_*` markers), so a worker keeps its family. A node or role may pin another.
`exec` is an escape hatch with a template, and an explicit `--exec-template`
always wins — which is why the whole executor is testable without a model.

### D5. Prompts are generated from the contract

`plan.Prompt` appends the artifact contract and the rules. A node may supply its
own task body, but never the acceptance criteria. This is what makes "done" mean
the same thing in every node.

### D6. WBS ids are hierarchical, estimates are advisory

`1.0` epic, `1.1` task, `1.1.2` subtask, matching the operator convention.
`estimate` feeds PERT, critical path, waves, and the `--workers` wall-clock
estimate. Nothing in verification reads it, so a bad estimate can only produce a
bad printout.

### D7. Export is a pure function of state

`export.AgilePlus` and `export.Tracera` read plan + state + trace and write JSON.
They never mutate. There is no live coupling to either system, so neither can
break a run.

### D8. Dynamic nodes live in state, not in the plan

A discover node names an artifact that lists units; when that artifact verifies,
the run gains one child node per unit. Those children are stored in
`state.Dynamic`, not in the plan, so the plan hash stays a hash of what the agent
wrote and a rerun cannot be rejected for "changing the plan".

Two consequences that are easy to get wrong:

1. **Expansion must be idempotent per parent, not per child.** Racing executors
   check one `expanded` marker under the same lock that inserts the children.
2. **The work set is the source of truth, not the LLM.** Because the work set is
   an ordinary verified artifact, re-expansion after a crash produces the same
   nodes. If discovery itself were a side-effecting call, a rerun could expand a
   different set and silently skip or duplicate work.

A template (`fan_out`) is structure, not work: it is never claimed, and it is
marked skipped once expanded so status and progress do not count it. A reduce
(`fan_in`) has its dependency list injected at expansion time, which is why it
cannot run early.

### D9. Windows is refused, not degraded

`flock` does not exist there. Rather than silently assuming one writer per run,
the windows build returns an error. macOS and Linux are the targets.

### D10. The console observes agents through one projection, never a second one

`GET /api/agents` and the viewer's card rail are the same data: `viz.Build`
calls `agents.BuildFrom` and embeds the result, so a page cannot disagree with
the API. Two consequences are deliberate.

*One identity implementation.* `session.Self` is the only place that reads the
process environment for harness/session identity; `dagrun session`, the agents
self card and the console banner all call it. A second copy is how the CLI and
the page start reporting different sessions for the same process.

*Observation only.* A card carries the session id the executor recorded plus
whether anything corroborated it (`session_validated`, `session_evidence`). An id
no on-disk artifact backs stays unvalidated: the console never promotes a claim
to a fact, and no card exposes a control that drives an agent. Terminal state
is read from artifacts and state files, never from a captured screen.

The rail and the graph are two views of one selection: a card click opens that
node, a node selection marks its card. That is why selection lives in one
variable rather than in each surface.

The UI test is headless and screenshot-free: `viewer.html`'s own script runs
under a small DOM shim in Node, and the assertions read the markup and panel
text it produced (`make test-ui`). Canvas pixels are not asserted; drawing is
verified through its inputs.

### D11. The applet surface publishes facts it can prove, behind two documents

A master console needs to discover this run, decide whether to mount it, and
render it without learning a bespoke API. That is three questions, and they are
answered by three routes, each with one job.

`/.well-known/applet.json` is the **manifest** and nothing else. It validates
against the shared contract `urn:phenotype:atlas-plan:1:applet`
(`docs/atlas/schemas/applet.schema.json`, byte-identical to the `docs-5` copy),
which sets `additionalProperties: false`. That clause is why the split exists: an
origin, a port and a mount path are deployment facts, and a manifest that carried
them could not be published by the same schema everywhere. The manifest is
checked in `server.New` and a server that cannot produce a conforming one refuses
to start, so a console never receives a document that fails its own contract.

`/api/applet` is the **discovery** document: the same manifest, embedded
unmodified, plus what only this process knows. `host.origin` is derived from the
request, never from `X-Forwarded-Proto`, because this server is loopback-only and
a proxy header here is a claim it cannot check. `authority` states that dagrun
owns the run and `writes` is false. `mount` states `read_only: true` and the
effective frame policy. `routes` lists the GET endpoints with `read_only: true`
on each, so a console can build a menu without a second fetch.

`/embed` is the mountable view. It is the agent-card projection rendered as one
page with the node table beside it, and it is built with the same `agents.Build`
that answers `/api/agents`, so the page and the API cannot disagree about which
session a node ran in or whether it was validated. It carries **no form, button,
input, select or textarea**, and the test asserts their absence rather than
reviewing the template once: a control here would turn a second console into a
write path onto somebody's agent session.

Authorization is stated rather than implied. The mode is `none-by-design` with
scope `loopback`, because the only people who can reach the port are already on
the machine. That makes framing the real boundary, so `frame-ancestors` starts at
`'self'` and widens only through an explicit `--embed-allow-origin`, one bare
origin at a time. `*` and a scheme wildcard are rejected at startup, and the
shipped CSP also carries `default-src 'none'` and `form-action 'none'`: the page
fetches nothing, posts nowhere, and can only be framed by an origin named on the
command line.

### D12. A running server advertises itself, so a launcher need not scan ports

The three routes above are only useful to a console that already knows the port.
A tray menu or a master app is started once and then has to find servers it did
not start, and port scanning is both slow and a false-positive machine on a
shared box. So `serve` writes one small JSON record per running server into a
registry directory, and `dagrun instances` reads it back.

The record is a rendezvous, not state: the contract urn, an `id` derived from
the bound port, the three absolute URLs (`manifest`, `discovery`, `embed`), the
working directory, version, pid, `started_at`, `read_only` and `allow_origins`.
The URLs are absolute on purpose. A host that concatenates paths is a host that
gets `/api//applet` on one version and `/embed/` on the next.

`NewInstance` **refuses a non-loopback origin**. The advertised surface is
unauthenticated by design (D11), so advertising it off-host would publish a port
that has no authorization story. `Validate` re-checks every field a host relies
on when a file is read, because a registry file is untrusted input: any process
on the machine can write one.

Writes are atomic (temp file, `0600`, `rename`) so a concurrent reader never sees
a half-written entry, and the file name derives from the port, so a restart at
the same port replaces its own record instead of accumulating duplicates.
Retraction is deferred on a clean stop, so a finished `serve` leaves no record
behind, while a crash leaves a stale one that `--verify` distinguishes by
fetching the manifest from the record's own origin.

`ReadInstances` returns the valid entries **plus one error per unreadable file**.
A corrupt record must not hide the good ones, and an empty list must not be
indistinguishable from an empty directory. A missing directory is empty, not an
error, because "no servers" is the normal state on a fresh machine.

Advertising is opt-in at the library boundary (`server.Options.InstanceDir` empty
means write nothing) and on by default at the CLI boundary, resolved through
`$DAGRUN_INSTANCE_DIR`, then `<config>/dagrun/instances`, then
`~/.dagrun/instances`. A library must not write to a home directory unasked; a
command the person typed may.

## Layering

```
plan      schema, structural validation, topo, PERT, prompt      (no I/O except Load)
verify    artifact predicates, check execution                   (reads the filesystem)
store     state document, flock, leases, epochs, caps            (the only writer)
trace     sharded append-only events
harness   detection + argv
run       scheduler, child supervision, outcome
export    agileplus / tracera / json
cmd_*     CLI surface
```

`verify` and `plan` have no back edges; `run` is the only package that combines
them.

## Size

Measured, not estimated. "Code" excludes blank lines and comment-only lines.

The per-area table that used to sit here was measured on the tree as it stood when this
document was written. Parallel lanes have since grown it by roughly an order of
magnitude, so a copied table would be a false claim within a day. It is retired in
favour of the numbers below plus the command that re-derives them.

```sh
# production and test line counts, per package, raw and code
find . -name '*.go' ! -name '*_test.go' -print0 | xargs -0 cat | wc -l
```

Measured 2026-11-24, at 29 packages: **23,483 raw / 18,058 code production lines**,
plus **17,750 raw / 15,197 code test lines**.

The two surfaces this design owns, same day, same method:

| surface | files | prod raw | prod code | test raw | test code |
|---|---|---|---|---|---|
| `internal/applet` | 4 (+2 tests) | 886 | 648 | 717 | 644 |
| `internal/server` | 3 (+2 tests) | 698 | 483 | 674 | 578 |

`internal/applet` was split at 398 raw lines to keep every file under the 350 target:
composition (`Build`, discovery, framing) in `applet.go`, rendering in `embed.go`, and
the publish-time gate in `validate.go`. The instance registry (D12) is a fourth file,
`instance.go` at 286 raw, split out rather than added to `applet.go` because a
rendezvous file and an HTTP projection fail for different reasons. Largest of the nine:
`applet.go` at 328 raw.

The 350-line target is met by those surfaces and is not met tree-wide:
`internal/run/run.go` is 697 lines and `internal/query/query.go` 507. Both predate this
design and are named here rather than quietly counted as compliant.

The original budget was 1–2k of code with a 5k hard cap. At 17.7k it is blown by more
than three times, which is a decision for whoever owns the wider tree rather than
something a surface-level change can fix. Recorded, not restated as compliant.

Where it would shrink if it had to (roughly 700 lines, in order of least loss):

1. `pert.go` wall-clock simulation and per-worker table (~80): keep the critical
   path and waves, drop the makespan heuristic.
2. `cmd_*.go` flag plumbing (~120): using stdlib `flag` unchanged would forbid
   `dagrun plan file.yaml --json`, which is worse than the lines it saves.
3. `export.go` `json` format (~40): `status --json` already exposes state.
4. `harness.go` `exec` template splitter (~50): replace with `sh -c`.
5. Per-kind default artifact contracts (~60): require every node to declare its
   own artifacts.

None of these were cut, because each removes something that earns its lines.

## Validation performed

- `go build ./...`, `go vet ./...` clean.
- `go test ./...` green; `-race` green on the concurrency-critical packages.
- 8 separate OS processes racing one claim → exactly one winner.
- 16 goroutines racing one claim → exactly one winner.
- lease expiry reclaims; stale-epoch `Finish` is rejected.
- global cap and per-role cap both block a second lease inside the lock.
- attempt budget exhausts to `failed`.
- end-to-end: 9-node DAG, 9/9 done via a stand-in agent, `validate` clean.
- idempotency: second run with a deliberately failing template still ends 9/9,
  all adopted, nothing spawned.
- failure path: a placeholder that misses `must_contain` is retried, then failed,
  and the run exits non-zero.

## Open questions

1. Should `dagrun run` auto-commit per node via the `git-commit` ledger wrapper?
2. Should `next --json` also emit TodoWrite-compatible items so a harness's todo
   UI mirrors the DAG?
3. Working-tree isolation for parallel nodes: `workdir` per node works, but a
   git-worktree-per-node mode would be strictly better.
4. Whether to add a `dagrun submit` that POSTs to Tracera's `/ingest/agileplus`
   rather than writing a file.
