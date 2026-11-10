# Absorption Manifest — dagrun

## Source

- **Repository:** `KooshaPari/dagrun`
- **Revision absorbed:** `8080d73ab40c346cae86e620e3426169a401365a` (`main`)
- **Commit count:** 53
- **Full history:** `dagrun-history.bundle` (this directory, 550 KiB) — a
  complete `--all` bundle. **Verified by restoring from it**, not by
  `git bundle verify`: the restore produced 53 commits and the identical `HEAD`.
  (`git bundle verify` passing does not prove a bundle is clonable.)
- **Uncommitted at merge time:** `internal/server/` (one file) — carried in the
  working-tree copy, because a bundle only contains committed history.

## Target

Whole-product absorption, not a file scatter. dagrun is one Go module and it
moved as one module.

| What | Destination | State |
|---|---|---|
| Entire module (195 files, 162 Go) | `cmd/dagrun/` (this repo), own `go.mod` | **absorbed 2026-11-10** |
| Full git history (53 commits) | `docs/absorbed-from-dagrun/dagrun-history.bundle` | **absorbed 2026-11-10** |
| `phenotype-dag-core` `DagSchema` shape | not yet absorbed — see below | **OPEN** |

The home follows this repo's convention: `cmd/wire`, `cmd/checker`,
`cmd/promptscrape`, `cmd/trust`, `cmd/capprobe` each carry their own `go.mod`.
The module path stays `github.com/KooshaPari/dagrun` rather than being rewritten
to `github.com/phenotype/fabric/cmd/dagrun`: rewriting it would touch every
internal import in ~40 files for no behavioural gain, and nothing consumes
dagrun as a library (it is a binary). Recorded here so the inconsistency is a
decision rather than an oversight.

## Lineage

dagrun is attempt **#4** of four (see `ADR-ECO-024` in `phenotype-registry`):

| # | Attempt | State |
|---|---|---|
| 1 | `dagctl` (external) | archived 2026-06-18, absorbed into phenodag |
| 2 | `phenodag` (Go) | repo deleted; absorption was recorded but never executed |
| 3 | `phenotype-dag-core` (Rust) | alive, zero consumers |
| 4 | `dagrun` (Go) | **this absorption** |

## Status

**Merge complete. NOT deletion-eligible yet.**

Gates from `ADR-ECO-024`:

| # | Gate | State |
|---|---|---|
| 1 | Absorbed behaviour exists with a test | PASS — whole module, full suite green |
| 2 | dagrun reads `phenotype-dag-core` `DagSchema` natively | **OPEN** |
| 3 | `go test ./...` green in the new home | PASS |
| 4 | Fresh clone builds and tests green | **PASS** — `git clone --branch feat/absorb-dagrun --depth 1`, then `go build` + `go test ./...` in `cmd/dagrun/`: exit 0; bundle restore from the clone produced 53 commits at `8080d73` |
| 5 | `bin/repo-delete-gate.sh` passes with this manifest | pending gate 2 |

Evidence for gate 3, run in `cmd/dagrun/` in the working tree:

```
gofmt -l .            -> no output
go vet ./...          -> exit 0
go test ./...         -> exit 0
go test -tags scale   -> exit 0
go test -race ./internal/server/ -> exit 0
```

### Why gate 2 is open, and why it is the one that matters

Gate 2 is what makes "one product" a fact instead of a claim. Four
implementations existed and **two of them defined a DAG schema for the same
ecosystem**. Merging the code without reconciling the schemas would move the
collision into a new directory and guarantee a fifth attempt.

Until dagrun reads a `DagSchema` document and a compatibility test proves the
two describe the same thing, `phenotype-dag-core` stays in the Rust workspace and
`KooshaPari/dagrun` stays on GitHub.

### If gate 2 cannot be satisfied

`ADR-ECO-024` commits to the opposite outcome in that case: if `DagSchema` turns
out to express something dagrun's plan genuinely cannot (typed audit hooks are
the plausible candidate), the correct answer is to **keep the crate and make
dagrun consume it**, not to force a fit. That would leave this absorption as a
relocation only, and the ADR should be amended rather than quietly ignored.

## What was deliberately NOT done

- No `git subtree` merge. The history is preserved as a verified bundle instead.
  A subtree merge rewrites 53 commits under a new prefix and makes the original
  hashes unaddressable; the bundle keeps them restorable and keeps this repo's
  history linear. Both are legitimate; this one is auditable with one command.
- No module-path rewrite (see above).
- No changes to `AgilePlus` or `Tracera`. They are consumers with a working
  export/import boundary, and coupling three repos for an unrequested benefit is
  not consolidation.

## Rollback

```sh
git clone docs/absorbed-from-dagrun/dagrun-history.bundle /tmp/dagrun-restored
# -> 53 commits, HEAD 8080d73, ready to push anywhere
```
