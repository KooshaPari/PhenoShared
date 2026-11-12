# dagrun consolidation decision

Recorded 2026-11-12. Every claim below cites a path or a SHA. Where the
evidence does not settle a question, the cell reads UNKNOWN and names the
command that would settle it.

## 1. What was consolidated, and where it lives now

dagrun is a Go module living inside this repository at `cmd/dagrun/`.

- Module path: `github.com/KooshaPari/dagrun` (`cmd/dagrun/go.mod:1`).
- Go directive: `go 1.25.0` (`cmd/dagrun/go.mod:3`).
- First commit that introduced `cmd/dagrun`:
  `cbd5f810a6c229c638ad97c7b8fe650bf0eea1c5`, 2026-11-10 00:33:24 -0800,
  "feat(absorb): absorb dagrun into cmd/dagrun as the one work-DAG product (#838)".
  That commit added 198 files and 39,925 lines under `cmd/dagrun/`;
  `git show --name-status cbd5f810a -- cmd/dagrun` reports 198 `A` entries and
  no other change type.
- `git log --follow --oneline -- cmd/dagrun/go.mod` returns exactly two commits:
  `cbd5f810a` (creation) and `dd498a88911aff7f29f368795b3647f3dc8535eb`
  (2026-11-10, "feat(mcp): serve the same tools over HTTP, from one catalogue
  (#893)"). The module's dependency set has changed once since it landed.

On disk today `cmd/dagrun/` holds 24 non-test `cmd_*.go` files, 24 packages
under `internal/`, 104 non-test `.go` files in total, 6 plan templates
(`internal/plan/templates/*.yaml`), 2 worked examples
(`examples/next-cvp/plan.yaml`, `examples/lint-fanout/plan.yaml`), and
`DESIGN.md`.

## 2. Why: PhenoShared is the substrate, dagrun is the execution layer

Decision: **dagrun lives inside PhenoShared, and dagrun is the execution layer
that runs on top of it.** PhenoShared holds the shared substrate; dagrun is the
component that schedules a work DAG and executes it against that substrate.

The history supports this as a decision already taken, not a proposal:

- `cbd5f810a` (2026-11-10) names the outcome in its own subject: dagrun was
  absorbed "as the one work-DAG product".
- The next commit, `4f38b647e38d6254e23a1e71456fcd72e2ddfa7f` (2026-11-10),
  "refactor(dag): drop phenotype-dag-core (ADR-ECO-024 gate 2 satisfied) (#844)",
  removed the alternative in-repo DAG core. dagrun is the survivor of that
  gate, not a second DAG implementation.
- `b882541efb426c14b5e4d3b493bc6ea11874a320` (2026-11-11), "ci(go): register
  cmd/dagrun in the Go module allowlist (#904)", wires the new module into this
  repository's Go CI, which is the practical form of "it belongs here".

## 3. What survived, what did not, and what is UNKNOWN

**Survived and observable on disk.** The module path and its dependency set
(`cmd/dagrun/go.mod`), 24 CLI command files, 24 `internal/` packages, the plan
templates, the two examples, `DESIGN.md`, and the `cmd/dagrun/docs/` note set
(`cli-audit.md`, `harness-notes.md`, `harness-proof.md`, `research.md`,
`scale.md`, plus a `research/` directory).

**Deliberately dropped.** The in-repo `phenotype-dag-core`, dropped by
`4f38b647e` under ADR-ECO-024 gate 2.

**UNKNOWN: whether the absorb was lossless.** This repository cannot answer
it. `git log --diff-filter=D --name-only -- '*dagrun*'` returns nothing: no
dagrun-named path was ever deleted here, so the absorb was an addition to this
repository, not a move within it. The pre-move source lived somewhere else and
its disappearance is invisible from this history. Settling it requires the
pre-move tree compared file-by-file against `cbd5f810a -- cmd/dagrun`; the
command that would settle it is a diff of the absorbed repository's tree at
the absorbed commit against `git show --name-status cbd5f810a -- cmd/dagrun`.
Until that comparison is run, "nothing was lost" is UNSUPPORTED here.

**UNKNOWN: which files in `cmd/dagrun/docs/` landed with the absorb.** Settling
it needs `git log --oneline -- cmd/dagrun/docs`.

## 4. The ownership boundary

dagrun owns, and the file where each responsibility was observed:

| dagrun owns | file observed |
|---|---|
| DAG scheduling, plan model, CVP, budgets | `internal/plan/plan.go` (`ArtifactsRoot`, line 110), `internal/plan/cvp.go`, `internal/plan/dagschema.go`, `internal/plan/discover.go`, `internal/plan/budget.go`; CLI `cmd_plan.go` |
| Harness execution | `internal/harness/harness.go`, `internal/harness/usage.go`, `internal/run/run.go`, `internal/run/exec.go` (spawns with `cmd.Dir = workdir`, line 122); CLI `cmd_run.go` |
| Artifact predicates | `internal/verify/verify.go` (artifact path resolves as `filepath.Join(root, a.Path)`, line 138; a node's `check` runs as `sh -c <command>` with the run root as cwd, line 303), `internal/verify/kinds.go` (per-kind contract checks, line 83) |
| Anti-gaming | `internal/verify/antigaming.go` (`PlaceholderFindings` line 46, `PaddingFindings` line 125, `CrossNodeDuplicates` line 167) |
| Trace | `internal/trace/trace.go`; merged by `internal/trace.Merge` in `cmd_timeline.go:23`, `internal/mcp/tools_more.go:376`, `internal/otel/otel.go:95` |
| AgilePlus export/import bridge | `internal/agileplus/agileplus.go` (package doc: "reads the ImportBundle that `dagrun export --format agileplus` emits, so a run can go to AgilePlus and come back"), `internal/export/export.go`, `internal/agileplus/agileplus_test.go:283` (`agileplus.map.json`); CLI `cmd_import.go` |

AgilePlus owns the backlog and feature lifecycle, spec artifacts, governance
rules and gates, the triaged queue, the retrospective, and elicitation. dagrun
implements none of them. Its only contact surface is the ImportBundle: dagrun
emits it with `dagrun export --format agileplus` and reads it back through
`internal/agileplus`. **Nothing in this epic may rebuild those AgilePlus
responsibilities inside dagrun.**

## 5. Non-goals, and what a reader should not conclude

Non-goals: dagrun does not own the backlog, the feature lifecycle, the spec
corpus, the governance rules, the queue, the retrospective, or the elicitation
interview. It does not own CI, harness vendors, or model providers; it spawns
them (`internal/harness`). This document records where the code lives, not a
rewrite of it.

A reader should NOT conclude:

- that the move was lossless (see the UNKNOWN in section 3);
- that dagrun's gates are proven correct by this document. That is a separate,
  executable claim, recorded in `TRACEABILITY.md` in this directory with its own
  probe and its own NOT_RUN cells;
- that dagrun enforces AgilePlus governance. It exports and imports a bundle;
  the lifecycle lives in AgilePlus;
- that moving dagrun back out of PhenoShared is available. `4f38b647e` dropped
  the alternative in-repo DAG core on the strength of ADR-ECO-024 gate 2, and
  `b882541ef` wired this module into the repository's Go CI.
