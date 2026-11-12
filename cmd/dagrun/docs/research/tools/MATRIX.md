# Tool comparison matrix: durable workflow / DAG orchestration

**Purpose.** Place `dagrun` against real, existing tools in this space on the dimensions
that decide whether you adopt one. `dagrun` is one column, filled from source, not from
assumption.

## How to read this document (verification limits)

- **The dagrun column was read from the code in this module.** Every dagrun cell cites the
  file that supports it. See [Citations](#citations-for-the-dagrun-column).
- **Every non-dagrun cell was filled from prior knowledge, not from upstream documentation.**
  No web research was performed in this pass and no upstream repository was opened. Those
  cells were **not** verified against vendor docs in this pass.
- **`?` means "I am not confident."** It is the correct answer wherever the author's
  recollection was partial, version-dependent, or simply absent. A confidently wrong cell is
  worse than a question mark, so the matrix deliberately contains many of them.
- **No version number, licence, or capability was invented for another tool.** Where a licence
  or a feature is remembered only vaguely, the cell is `?`.
- Negative claims for another tool (`No ...`) are used only where the absence is a defining
  property of that tool's model, not where it is merely unknown. Where absence was uncertain,
  the cell is `?`.

## The comparands

Ten tools: `Make`, `Luigi`, `Nextflow`, `Airflow`, `Prefect`, `Dagster`, `Argo Workflows`,
`Temporal`, `GitHub Actions`, and `dagrun`.

They are not the same category. `Make` is a build driver, `Temporal` is a durable execution
engine, `Argo` is a Kubernetes controller, and `dagrun` is an agent-facing work-DAG executor.
The matrix compares them on execution semantics, which is the shared axis, not on product
scope, which is not shared.

## The matrix

| Tool | Language of implementation | Definition format | Execution model | Artifact / data gating | Resumability after failure | Provenance / trace model | Multi-harness or agent support | Local-first vs server-required | Licensing |
|---|---|---|---|---|---|---|---|---|---|
| **Make** (GNU) | C | `Makefile` rule/target syntax | Single process; recursive recipe execution | File existence + mtime per target; no content predicate | Re-run skips targets that are newer than prerequisites | stdout log only; no structured history | No (no agent-harness model) | Local-only | GPLv3 |
| **Luigi** | Python | Python task classes with `requires()`/`output()` | Central scheduler + workers (local or clustered) | **Strong**: `complete()` is true only when the declared `Output` target exists | Re-run skips tasks whose outputs already exist | Central scheduler UI; task history in scheduler memory, limited durability | ? | Local scheduler possible (`luigid` optional) | Apache-2.0 |
| **Nextflow** | Groovy / Java (DSL2) | `main.nf` workflow/process DSL + `nextflow.config` | Pluggable executors (local, SLURM, Kubernetes, cloud batch) | `?` (process declares `output:` path patterns and `publishDir`; whether a missing output fails the task is not asserted here) | **`-resume`** via per-task hash cache | `.nextflow.log`, `-with-trace`, `-with-report` | ? | Local executor available; no server required | Apache-2.0 |
| **Airflow** | Python | Python DAG code | Scheduler + executor (local, Celery, Kubernetes) | `?` (task state, not artifact content, is the success signal; data-aware scheduling exists but was not verified here) | Per-task retries; recover by clearing/re-running failed tasks | Task-instance history in a metadata DB; task logs in the UI | ? | Server components required (scheduler + metadata DB) | Apache-2.0 |
| **Prefect** | Python | Python flows/tasks with decorators | Orchestration API + work pools / workers | Artifacts are published metadata, not an execution gate | Per-task retries; persistent task-result cache allows skipping completed work | Event/automation log plus flow-run UI | ? | Local ephemeral API is possible; a server component is the normal shape | Apache-2.0 |
| **Dagster** | Python | Python asset / job graph | Daemon + run launcher (local, K8s, Celery) | Asset dependencies enforce ordering; no content predicate on materialisation | Re-execution with retries; partial re-execution supported | Asset materialisation events + event log catalog | ? | `dagster dev` runs locally; daemon for production | Apache-2.0 |
| **Argo Workflows** | Go | Kubernetes CRD (YAML `Workflow`) | One pod per step on a Kubernetes cluster | `?` (outputs/artifacts are declared and stored; whether artifact absence fails the step is not asserted here) | `retryStrategy`; resubmit a workflow | Workflow status object; archived workflows | ? | Requires a Kubernetes cluster | Apache-2.0 |
| **Temporal** | Go (server) + polyglot SDKs | Workflow code (Go, Java, TypeScript, Python, …) | Durable execution service + task-queue workers | `?` (no native artifact semantics) | **Strongest**: deterministic replay from persisted event history | Per-execution event history (the history *is* the provenance) | ? | Server required; a single-node dev server is bundled | MIT |
| **GitHub Actions** | `?` (hosted service; the runner is a separate open-source component) | YAML workflow files | Jobs and steps on hosted or self-hosted runners | Not the gate: job success is exit status; `actions/upload-artifact` stores outputs separately | Re-run failed jobs, not mid-job resume | Run logs + stored artifacts | ? | Hosted, or self-hosted runner that still talks to GitHub | `?` (hosted service terms; component licences vary) |
| **dagrun** | Go (`go 1.25.0`, module `github.com/KooshaPari/dagrun`) — `go.mod` | YAML plan: nodes with `id`/`kind`/`deps`/`artifacts` — `internal/plan/plan.go:67-81` | Local single binary; wave/readiness scheduler; also agent-driven `next` → `claim` → `done` mode — `internal/store/lease.go`, `internal/store/store.go:31-45` | **Core invariant**: a node is done only when every declared artifact satisfies its predicate (`path`, `min_bytes`, `must_contain`, `must_match`, `min_count`) — `internal/verify/verify.go:1-5`, `internal/plan/plan.go:53-62` | On-disk `state.json` under `flock`, tmp+fsync+rename; adopted rather than resumed, since re-verified artifacts mean done — `internal/store/store.go:54-68`, `DESIGN.md` D1/D2 | The DAG is the trace: sharded event writer merged per run — `internal/trace/trace.go:22-152` | **Five harness adapters**: `jcode`, `kcode`, `codex`, `forge`, `helioslite` — `internal/harness/harness.go:56` | **Local-first**: one binary, no daemon, no database — `README.md`; optional read-only local HTTP surface — `internal/server/server.go:1-12` | MIT (`LICENSE`) |

## Where dagrun is genuinely differentiated

**Differentiated:** `dagrun` is the only tool here where "done" is defined as a *content
predicate on a declared artifact* rather than as a process exit code or a scheduler state
transition, and it is enforced by a verifier that explicitly refuses to consult a model
(`internal/verify/verify.go:1-5`, predicate fields at `internal/plan/plan.go:53-62`, invariant
stated in `DESIGN.md` §"The one invariant"). Luigi is the nearest neighbour — its `complete()`
also keys on an output target — but Luigi checks existence of a target object, not
`min_bytes` / `must_contain` / `must_match` / `min_count` predicates, and it has no notion of
routing a node to a coding-agent harness.

## Where dagrun is clearly behind

**Behind:** `dagrun` has no distributed scheduler, no durable server-side engine, and no
multi-node execution — its state is one local `state.json` guarded by `flock` (`DESIGN.md` D1)
and its HTTP surface is read-only by construction (`internal/server/server.go:1-12`) — whereas
Temporal replays durable event histories and Argo fans out across a Kubernetes cluster. It is
also behind on ecosystem breadth: one direct dependency (`gopkg.in/yaml.v3`) in `go.mod`
against the connector and executor catalogues of Airflow, Dagster, and Nextflow.

## Citations for the dagrun column

| Claim | File:line |
|---|---|
| Implementation language / module / Go version | `go.mod:1-3` |
| YAML plan schema, node fields, artifact predicates | `internal/plan/plan.go:42-62`, `internal/plan/plan.go:67-81` |
| Verification rule (no model, no trust in a claim) | `internal/verify/verify.go:1-5` |
| Per-run state, node lifecycle fields, adoption-not-resume | `internal/store/store.go:31-68`; `DESIGN.md` D1, D2 |
| Trace model (sharded events, merged, rendered) | `internal/trace/trace.go:22-152` |
| Harness adapters and resolution order | `internal/harness/harness.go:56-61` |
| Read-only local HTTP surface | `internal/server/server.go:1-12` |
| Local-first positioning ("one binary, no daemon, no database") | `README.md` |
| Licence | `LICENSE:1` |

## Open items that would firm up this matrix

These are the cells most likely to change on a real documentation pass, listed so the next
author does not have to rediscover them:

1. Airflow, Argo, Nextflow, and Temporal artifact-gating cells — all `?`. Whether an absent
   declared output *fails* the step is the exact question this matrix asks and the exact
   question prior knowledge does not answer.
2. The multi-harness / agent-support column — eight of ten cells are `?` (only `Make`, which is
   `No`, and `dagrun`, which is filled from source, are answered). Several of these tools
   have acquired LLM- or agent-oriented operators/integrations whose scope was not verified.
3. GitHub Actions' implementation language and licence — both `?` because the hosted service
   and its open-source runner are separable and the licence applies per component.

---

Status: draft, authored 2026-11-12 (UTC) from module state at commit 128b9f1982a96fe9e90f8c0130176d84b862a52a
