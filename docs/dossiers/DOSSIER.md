# PhenoShared — Dossier

Deliverable: **D15.1**. Status: first edition.

## 0. Provenance of this document

Every value below is either (a) measured by a command run on 2026-11-12
against the working tree at commit `5154a6828`, or (b) explicitly labelled
as a *claim* reported by a source file in this repository that was **not**
re-measured here. Values that could not be established are written as
`UNKNOWN` together with the command that would settle them.

Structure note: this dossier was specified to mirror
`phenotype-omlx/docs/dossiers/DOSSIER.md`. **That path does not exist** —
neither under `~/CodeProjects/Phenotype/repos/phenotype-omlx/` nor anywhere
within four levels of this repository's root (`find . -maxdepth 4 -name
DOSSIER.md` returned nothing). The heading structure below is therefore the
generic dossier shape described in the docs-3/atlas programme (identity,
absorption, architecture, quality, risks, evidence), not a copy of a file
that could not be read. If the PhenoMLX dossier is restored, this section
should be updated to say which headings were mirrored.

## 1. Identity

| Field | Value | Source |
| --- | --- | --- |
| Repository | `KooshaPari/PhenoShared` | `README.md` |
| Local clone alias | often checked out as `repos/pheno`; `KooshaPari/pheno` redirects to `KooshaPari/PhenoShared` | `README.md` |
| Role | container repository: shared Rust crates, reusable GitHub workflows/composite actions, shared documentation (Global Handbook) | `README.md` |
| Workspace version | `0.3.10` | `README.md` at-a-glance table |
| Rust edition / MSRV | 2021 / `rust-version = "1.80"` | `README.md` at-a-glance table |
| Unsafe policy | `forbid` workspace-wide | `README.md` at-a-glance table |
| License | `MIT OR Apache-2.0` (`LICENSE-MIT`, `LICENSE-APACHE`) | `README.md` |
| Object under assessment | the root Cargo workspace + the non-Rust trees it carries | this document |

This is a **container**, not a single product. It is one workspace holding
many independently consumable crates plus non-Rust assets. Treating it as
one shippable artifact is the most common misreading of this repository.

## 2. Measured shape (2026-11-12)

Command: `cargo metadata --no-deps --format-version 1`, parsed in place.

| Metric | Measured | Note |
| --- | --- | --- |
| `workspace_members` | **291** | |
| `packages` returned by `--no-deps` | **291** | equals members, i.e. no path-only non-member packages reported |
| Members under `crates/` | **267** | |
| Members under `absorption/` | **20** | all under `absorption/PhenoMLX-temp/perf-core/` |
| Members under `tools/` | **2** | `fake-codex-cloud`, `fake-forge` |
| Members under `examples/` | **1** | `fabric-full-demo` (`examples/full-demo`) |
| Members under `native/` | **1** | `playcua-native` |
| Crates with **no** in-workspace dependent | **170** | counted from the same metadata; these are publication/consumer or deletion candidates, not necessarily dead code |
| Most-depended-on crate | `substrate-core` — **36** workspace dependents | |
| Next highest | `fabric-capability` 15, `engine-spec` 12, `fabric-graph` 12, `focus-domain` 10 | |

Per-crate boundaries, paths and dependents are in [`../CRATE-BOUNDARIES.md`](../CRATE-BOUNDARIES.md)
(deliverable D15.2), generated from this same metadata run.

### 2.1 Discrepancy to be aware of

`README.md`'s at-a-glance table states **290** root workspace packages
measured 2026-11-11; the metadata run on 2026-11-12 reports **291**. The
README does not say which package was added, and this dossier does not
assert a cause. Reconciling the two member sets needs a diff of the two
lists, which this pass did not run (see open question 1).

## 3. Absorption history (evidence-backed)

The only absorption visible as *workspace members* is PhenoMLX: all 20
`absorption/` members live under `absorption/PhenoMLX-temp/perf-core/`
(`concurrent-exec`, `kernel-registry`, `metal-runtime`, `model-kernels`,
`spec-decode`, `tree-attention`, the `turbo-quant` family, `native-abi`,
`fleet-proto`, and so on). Note this means the PhenoMLX code is present
**inside this workspace** at a `-temp` path, which is not a stable-looking
location; whether it is intended to stay there is `UNKNOWN`.

Other absorbed material exists as non-member directories
(`docs/absorbed-from-*`, `absorption/`), which are outside the Cargo
workspace and therefore invisible to `cargo metadata`. A fuller
chronological absorption account is maintained in
`docs/dossiers/HANDOFF-PHENOSHARED.md` ("Absorption History") and
`docs/ABSORPTION_INDEX.md`; this dossier cites them rather than restating
them, and did not re-verify their claims.

## 4. Non-Rust surface

Reported by `README.md` (measured there on 2026-11-11; **not** re-measured here):

| Area | Claimed count |
| --- | --- |
| Reusable workflow files under `.github/workflows/` | 90 |
| Composite actions under `.github/actions/` | 6 |
| Markdown files under `docs/` | 2,668 |
| ADRs | 82 in `docs/adr/`, 25 in `docs/adrs/` |
| Registered project manifests | 178 (`projects/*.json`) |

Independently observed on 2026-11-12 while surveying the tree: `cmd/`
contains six sub-directories — `capprobe`, `checker`, `dagrun`,
`promptscrape`, `trust`, `wire` — of which `cmd/dagrun` is a **separate Go
module** (`module github.com/KooshaPari/dagrun`, `go 1.25.0`) and is
therefore invisible to `cargo metadata`. Whether the other five are Go,
Rust, or something else was not established: `UNKNOWN` (settle with
`ls cmd/<name>` plus each `go.mod`/`Cargo.toml`).

## 5. Compilation and test status

`UNKNOWN`. This dossier was produced under a lane rule that forbids
`cargo build` and `cargo test` (build-slot contention), so no compile or
test result is claimed.

What would settle it: `cargo check --workspace --all-targets` for Rust and
`go build ./...` plus `go test ./...` inside `cmd/dagrun`, each recorded
with its exact rustc/go version. Until such output exists, a statement that
PhenoShared "builds" has no source in this document.

## 6. Capability inventory (what the workspace actually provides)

Derived from crate names, paths and dependency edges in the metadata. This
is a *map*, not an adoption claim.

| Family | Members | What it appears to own |
| --- | --- | --- |
| `substrate-*` | ~20 | agent-execution substrate: core, app, browser stack, dag, memory, schedule, skills, trace, tui. `substrate-core` is the single most-depended-on crate (36). |
| `driver-*` / `engine-*` | ~20 | separable driver (argv/cli/http/mcp) and engine (claude/codex/forge/agentapi/a2a/spec/conformance) traits |
| `fabric-*` | ~20 | desktop capture/orchestration fabric: capability, capture, graph, daemon, gui, tray, tui, terminal, web |
| `focus-*` | ~33 | a focus/discipline product line: domain, events, rituals, rules, rewards, penalties, scheduler, ui, sync |
| `sharecli-*` | ~14 | CLI/fleet/mesh/fuse/ipc/sync/session/tray surface over `sharecli` |
| `teamcomm-*` | ~6 | team communication protocol, client, daemon, mcp, smoke |
| `agileplus-*` | ~12 | spec-driven development domain: cache, domain, events, git, github, graph, import, nats, triage |
| `hwledger-*` | ~11 | hardware ledger plus a model-explorer search stack (core, index, ingest, rag, skills, tags, server, mcp) |
| `eyetracker-*` | ~8 | eye-tracking: camera, core, domain, ffi, inference, math, cli |
| `pheno-compose-*` / `phenocompose-*` | ~14 | compose-style container/port runtime with port-traits and adapter implementations |
| `pine-*` | ~6 | a sandbox/syscall-runtime line: core, compat, loader, nvms, syscall |
| `phenotype-*` | ~45 | org-wide primitives: errors, config, crypto, observability, retry, rate-limit, ports, tracing, telemetry |
| `pheno-*` (minus above) | ~15 | smaller shared utilities (fs, net, shell, i18n, crypto, otel) |
| `absorption/*` | 20 | absorbed PhenoMLX perf core |
| `tools/`, `examples/`, `native/` | 4 | fakes for testing, one demo binary, one native binding |

## 7. Quality gates

| Gate | State | Evidence |
| --- | --- | --- |
| Coverage floor (85%, docs-3 contract) | `UNKNOWN` | no coverage artifact was inspected in this pass; `codecov.yml` and `tarpaulin.toml` exist, which indicates an intention, not a measurement |
| Negative controls / instrument qualification | `UNKNOWN` | not inspected |
| Lint / fmt configuration present | yes | `rustfmt.toml`, `clippy` lints in workspace `Cargo.toml` (README), `ruff.toml`, `oxlint.json`, `deny.toml`, `gitleaks.toml`, `trufflehog.yml` |
| Unsafe forbidden | `UNKNOWN` | `README.md` states the policy; this pass did not read the workspace `Cargo.toml` lint table for it (open question 5) |

A configuration file records an intention; it is not an observed result. A
row above marked `UNKNOWN` stays `UNKNOWN` until a command's output is
recorded beside it.

## 8. Risks

| # | Risk | Why it matters | Control / next step |
| --- | --- | --- | --- |
| R1 | **Container-as-product confusion** | Consumers may try to build/adopt the whole workspace; it is a container of independently consumable crates | README states the role explicitly; keep it prominent |
| R2 | **Absorbed code at a `-temp` path** | `absorption/PhenoMLX-temp/perf-core/*` occupying 20 workspace members implies an unfinished absorption | Decide: promote to `crates/`, or remove from members. Owner `UNKNOWN` |
| R3 | **170 of 291 crates have no in-workspace dependent** | Large surface with no internal proof of use; unclear publish intent | Classify each as publish / consume-externally / delete; this pass produced the count only, by parsing `cargo metadata` (see appendix) |
| R4 | **README metrics drift** | 290 vs 291 packages already diverges within one day | Regenerate the at-a-glance table from a command, with the date in the file |
| R5 | **Truncated top-level tree** | `find . -maxdepth 1` alone shows a very large number of root-level markdown and scratch files (`_*.json`, diagnostic reports, `node_modules`, `target`), which obscures the real entry points | Read `README.md` as the entrypoint; do not infer structure from a root listing |
| R6 | **No measured build/test state** | An unmeasured container of 291 crates can rot silently | Run `cargo check --workspace` on a schedule and record the result here |

## 9. Open questions

1. Which single package was added between the README's 290 and the measured
   291? A diff of the two member lists would answer it.
2. Are the 20 `absorption/PhenoMLX-temp/perf-core` members permanent, or
   pending relocation?
3. Is there a published subset manifest (a list of crates intended for
   crates.io)? `sdk-catalog.json` and `catalog/` exist; their contents were
   not read in this pass.
4. Do the five non-`dagrun` directories under `cmd/` belong to the Rust
   workspace, to separate Go modules, or to neither?
5. Does the workspace `Cargo.toml` deny `unsafe`? The table row above cites
   `README.md`; the lint table itself was not read here.

## 10. Evidence appendix

| Claim | Command | Result |
| --- | --- | --- |
| Workspace member count and paths | `cargo metadata --no-deps --format-version 1` | 291 members, exit 0 |
| Layer distribution | parse of the same JSON | crates 267, absorption 20, tools 2, examples 1, native 1 |
| Crates with zero dependents | parse of the same JSON | 170 |
| `docs/dossiers/DOSSIER.md` did not previously exist | `test -f` | MISSING |
| No dossier anywhere in-repo | `find . -maxdepth 4 -name DOSSIER.md` | no output |
| `cmd/dagrun` is a separate Go module | `head -3 cmd/dagrun/go.mod` | `module github.com/KooshaPari/dagrun`, `go 1.25.0` |
| Dagrun docs already present | `wc -l cmd/dagrun/CONSOLIDATION.md cmd/dagrun/TRACEABILITY.md` | present (see D16.3, D16.4) |
