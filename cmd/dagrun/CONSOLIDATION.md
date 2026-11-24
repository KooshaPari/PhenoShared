# cmd/dagrun — consolidation decision record

Every statement below was produced by a command run against this module at the commit
named at the bottom of the file. Where a question could not be settled from the source, it
appears in "Open questions" rather than as an assumption.

## 1. Scope

`cmd/dagrun` is a self-contained Go module: `go.mod` declares
`module github.com/KooshaPari/dagrun`, `go 1.25.0`, one direct dependency `gopkg.in/yaml.v3`
plus `github.com/modelcontextprotocol/go-sdk` in the second `require` block, everything else
`// indirect`.

Measured with `ls` and by counting `package` declarations:

| Area | Files | Packages |
|---|---|---|
| `cmd/dagrun` top level | 28 (24 non-test `cmd_*.go` + `main.go`; tests `cmd_explain_test.go`, `cmd_import_test.go`, `main_test.go`) | 1 (`package main`, 28 declarations) |
| `internal/` | 144 | 24 |
| Total `*.go` | 172 (104 non-test, 68 test) | 25 |

File count per concern for the 24 non-test `cmd_*.go` files, by size
(`wc -l cmd_*.go`):

| Concern | File | Lines |
|---|---|---|
| explain | `cmd_explain.go` | 432 |
| view (status/trace/export/detect) | `cmd_view.go` | 382 |
| next (claim/next/ready) | `cmd_next.go` | 256 |
| workspace | `cmd_workspace.go` | 236 |
| run | `cmd_run.go` | 220 |
| node (claim/done/fail/skip/terminal/validate) | `cmd_node.go` | 218 |
| plan | `cmd_plan.go` | 186 |
| house (doctor/gc) | `cmd_house.go` | 135 |
| import / serve | `cmd_import.go` / `cmd_serve.go` | 127 / 127 |
| recover | `cmd_recover.go` | 112 |
| submit | `cmd_submit.go` | 111 |
| replan | `cmd_replan.go` | 110 |
| template | `cmd_template.go` | 105 |
| report (critique/review) | `cmd_report.go` | 104 |
| mcp | `cmd_mcp.go` | 102 |
| draft | `cmd_draft.go` | 88 |
| viz | `cmd_viz.go` | 87 |
| query | `cmd_query.go` | 86 |
| lint | `cmd_lint.go` | 85 |
| otel | `cmd_otel.go` | 46 |
| stats | `cmd_stats.go` | 36 |
| timeline | `cmd_timeline.go` | 35 |
| skill | `cmd_skill.go` | 22 |

`internal/` package sizes (`files`, `lines`, counted per directory):

`plan` 34/7065 · `run` 18/3518 · `mcp` 12/3153 · `store` 14/2391 · `verify` 15/2349 ·
`workspace` 10/2079 · `tracera` 4/1057 · `house` 4/980 · `query` 2/967 · `agileplus` 2/917 ·
`viz` 2/825 · `harness` 4/717 · `otel` 2/699 · `server` 2/686 · `report` 2/588 · `stats` 2/566 ·
`recover` 2/552 · `replan` 2/523 · `hook` 4/392 · `export` 1/373 · `skill` 2/358 ·
`diffscope` 2/322 · `trace` 1/170 · `timeline` 1/161.

Only three nested directories exist under `internal/`: `mcp/testdata`, `plan/templates`,
`plan/testdata`. There is no deeper package nesting, so the 24 packages are all flat
siblings.

## 2. Current structural facts

**One entrypoint.** `main.go` (297 lines) holds `func main()`; there is no cobra and no
`cmd/root.go`. Dispatch is a hand-written `switch cmd` over `os.Args[1]` and `os.Args[2:]`,
with `usage(w *os.File)` at `main.go:127` and one `default:` that prints an unknown-command
error and exits 2.

**33 dispatched commands, 34 handler functions.** The switch contains 33 `err = cmdX(args)`
arms across 35 `case` lines (the extras are the grouped `"version", "--version", "-v"` and
`"help", "--help", "-h"` arms, which call `fmt.Printf` and `usage` directly). The 34th
handler, `cmdTerminal` (`cmd_node.go:99`), is not a command: it is the shared implementation
that `cmdFail` (`cmd_node.go:96`) and `cmdSkip` (`cmd_node.go:97`) each wrap in one line.
That is an existing, correct consolidation, not dead code.

**Commands are grouped by file, not by use.** Verified handler-to-file map:

- `cmd_node.go` — `cmdClaim`, `cmdDone`, `cmdFail`, `cmdSkip`, `cmdTerminal`, `cmdValidate` (6)
- `cmd_view.go` — `cmdStatus`, `cmdTrace`, `cmdExport`, `cmdDetect` (4), plus unexported
  helpers `watchStatus`, `allTerminal`, `isTTY`, `printStatus`, `filterEvents`, `globMatch`,
  `orUnknown`
- `cmd_report.go` — `cmdCritique`, `cmdReview` (2), plus package-level `loadPlan(dir, file)`
- `cmd_house.go` — `cmdDoctor`, `cmdGC` (2)
- every other file holds exactly one handler.

**Cross-package duplication that actually exists.** Two things, both small:

1. `loadPlan` is defined twice under the same name for the same job:
   `cmd_report.go:85 func loadPlan(dir, file string) (*plan.Plan, error)` and
   `internal/recover/recover.go:153 func loadPlan(dir string) (*plan.Plan, []byte, error)`.
   The main-package copy has exactly one call site (`cmd_report.go`, 2 matches including the
   definition); the recover copy has 3. They differ in signature, so this is shared intent,
   not shared code.
2. CLI flag scaffolding. 9 of the 24 non-test `cmd_*.go` files open a flag set with
   `flag.NewFlagSet(..., flag.ContinueOnError)` and 9 call `fs.SetOutput(os.Stderr)`; 6
   declare `fs.String("dir", defaultDir, ...)`. The other 15 files use some other path, so the
   repetition is real but partial, not universal.

**Duplication that does not exist.** In `internal/plan`, the only repeated top-level function
name among 34 files is `Validate`, which is two methods on distinct receivers —
`func (p *Plan) Validate()` (`internal/plan/validate.go:13`) and
`func (p ProviderPolicy) Validate()` (`internal/plan/provider.go:94`). That is Go method
namespacing, not duplication. `internal/plan` is 34 files but its largest file is
`dagschema.go` at 445 lines; the file count reflects many small domain files (budget, cvp,
pert, replan, provider, scope, semantic, requirements, discover, calibrate), not sprawl.

## 3. Consolidation decision

The honest headline: **this module does not need a structural consolidation now.** It has one
entrypoint, one dispatch switch, a correct existing helper consolidation (`cmdTerminal`), and
its largest package is large by file count but small by file size. Four narrow changes are
worth naming; only P1 is worth doing before other work.

### P1 — Extract a shared CLI scaffold into `cmd/dagrun/flags.go` (worth doing: yes, low risk)

**What merges into what.** The 9 duplicated `flag.NewFlagSet(..., flag.ContinueOnError)` +
`fs.SetOutput(os.Stderr)` pairs and the 6 duplicated `fs.String("dir", defaultDir, ...)`
declarations become one `newFlagSet(name string) *flag.FlagSet` plus one
`addDirFlag(fs *flag.FlagSet, dir *string)` in a new file in `package main`.

**Evidence.** Per-file counts above; `flag.ContinueOnError` appears in 9 `cmd_*.go` files and
`fs.SetOutput(os.Stderr)` in 9.

**Risk.** Usage text and `--help` output are a certified regression surface:
`docs/cli-audit.md` records "26 commands. 26 now exit 0 on `--help`" and explains that the
`flag.ErrHelp` handling in `main.go` is what fixed the previous 24-of-26 false failures. Any
change to flag-set construction can perturb that.

**Test that proves it safe.** Re-run the audit procedure documented in `docs/cli-audit.md`:
build the binary, run every command's `--help` with the exit code measured **unpiped**
(`docs/cli-audit.md` notes a pipe masks the code), and diff the usage text before and after.

### P2 — Split `cmd_view.go` into one file per command (worth doing: not now)

**What merges into what.** `cmdExport`, `cmdTrace`, `cmdDetect` would leave `cmd_view.go`;
`cmdStatus` keeps the file, or it is renamed `cmd_status.go`.

**Evidence.** `cmd_view.go` holds four unrelated handlers plus seven helpers
(`printStatus`, `filterEvents`, `globMatch`, `isTTY`, `allTerminal`, `watchStatus`,
`orUnknown`); `cmdExport` shares no helper with `printStatus`.

**Risk.** `cmdStatus` and `cmdTrace` *do* share `printStatus`, `filterEvents`, `globMatch`,
and `isTTY`, so a split has to keep those four co-located or promote them. This is a
file-naming legibility change, not a coupling fix — which is exactly why it loses to P1.

**Test that proves it safe.** `go vet`/`go test` over `package main` still compiling is the
entire proof for a move within one package; `cmd_explain_test.go` and `cmd_import_test.go`
show the existing precedent that handlers are exercised from in-package tests.

### P3 — Fold `main.loadPlan` into `internal/plan` (worth doing: no)

**What merges into what.** `cmd_report.go:85 loadPlan(dir, file string)` becomes a call into
a single `plan`-package resolver shared with `internal/recover/recover.go:153 loadPlan(dir)`.

**Evidence.** Two same-named functions performing the same resolve-and-parse step, one per
package.

**Risk.** The main copy takes a `file` override that the recover copy does not, so a merge
must define which semantics wins; recover's 3 call sites would silently change if the
override path leaked in.

**Verdict.** One call site in `package main` does not justify touching a package that
`internal/recover`, `internal/run`, and the MCP layer also depend on. Revisit only if a third
caller appears.

### P4 — Merge `internal/diffscope` into `internal/run` (worth doing: after P1, if the owner agrees)

**What merges into what.** `internal/diffscope` (2 files, 322 lines) into `internal/run`
(18 files, 3518 lines).

**Evidence.** `rg -l 'internal/diffscope'` returns exactly one importer:
`internal/run/exec.go`. A package with a single consumer is a candidate for inlining.

**Risk.** It is a named seam. If a test or a second consumer is intended, merging destroys the
boundary; `diffscope` is small enough that the merge buys little.

**Test that proves it safe.** `go test ./internal/run/ ./internal/diffscope/` must pass with
the diffscope tests moved, unchanged, into the run package.

**Explicitly not proposed.** No consolidation inside `internal/plan` (no duplicated top-level
functions were found — only two `Validate` methods on distinct receivers) and none between
`internal/trace` (1 file, 170 lines) and `internal/timeline` (1 file, 161 lines): a one-file
package is a seam, and low line count is not evidence of redundancy.

## 4. Rejected alternatives

- **Adopt cobra / urfave-cli.** `go.mod` has no CLI framework, the whole dispatch is 35 case
  lines in a 297-line `main.go`, and adding a framework to a module whose direct deps are
  `yaml.v3` and the MCP SDK is disproportionate.
- **Replace the `switch` with a `map[string]func([]string) error` table.** Saves ~30 lines,
  buys a second place for `usage()` to drift out of sync with reality. Rejected because the
  switch is already the single source of truth next to `usage(w)`.
- **Split `internal/plan` by subdomain.** 34 files, but the largest is 445 lines and the file
  count is made of small domain files already; splitting would add package boundaries to code
  that shares one plan model.
- **Delete `cmdTerminal` and inline it into `cmdFail`/`cmdSkip`.** It is the correct existing
  consolidation; inlining would duplicate the body twice.
- **Move handlers into `internal/cli` so they become importable.** They are `package main` by
  design (they call `os.Exit`, print to `os.Stdout`), and no second binary consumes them.

## 5. Open questions for a maintainer

1. Does `main_test.go` already assert that every `case` in `main.go` has a `usage()` line and
   vice versa? The switch has 33 dispatched arms and `usage` is hand-maintained, so parity is
   currently unverified from the outside.
2. Is `cmd_view.go` named for a domain, or is "view" a leftover grouping? It holds
   `cmdStatus`, `cmdTrace`, `cmdExport`, `cmdDetect` (`cmd_view.go`).
3. Is `internal/diffscope` intended to have one consumer only? `rg` finds
   `internal/run/exec.go` as its sole importer, which is what makes P4 defensible.
4. Should `internal/agileplus` (2 files, 917 lines) and `internal/tracera` (4 files, 1057
   lines) — product-named packages inside a deliberately product-neutral executor, per
   `README.md` ("It is not tied to code") — stay in this module, or become adapters?
5. Why do 15 of 24 `cmd_*.go` files not use the `flag.NewFlagSet` + `SetOutput(os.Stderr)`
   pattern the other 9 use? That asymmetry is what makes P1 a partial refactor rather than a
   mechanical one; the outlier pattern needs to be named before `flags.go` is written.

Status: draft, authored 2026-11-12 from module state at commit 128b9f198
