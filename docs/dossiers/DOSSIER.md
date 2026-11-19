# PhenoShared — Dossier

Deliverable: **D15.1**. Status: first edition.

## 0. Provenance of this document

Every value below is either (a) measured by a command run on 2026-11-12
against the working tree at commit `5154a6828`, or (b) explicitly labelled
as a _claim_ reported by a source file in this repository that was **not**
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

| Field                   | Value                                                                                                                         | Source                        |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| Repository              | `KooshaPari/PhenoShared`                                                                                                      | `README.md`                   |
| Local clone alias       | often checked out as `repos/pheno`; `KooshaPari/pheno` redirects to `KooshaPari/PhenoShared`                                  | `README.md`                   |
| Role                    | container repository: shared Rust crates, reusable GitHub workflows/composite actions, shared documentation (Global Handbook) | `README.md`                   |
| Workspace version       | `0.3.10`                                                                                                                      | `README.md` at-a-glance table |
| Rust edition / MSRV     | 2021 / `rust-version = "1.80"`                                                                                                | `README.md` at-a-glance table |
| Unsafe policy           | `forbid` workspace-wide                                                                                                       | `README.md` at-a-glance table |
| License                 | `MIT OR Apache-2.0` (`LICENSE-MIT`, `LICENSE-APACHE`)                                                                         | `README.md`                   |
| Object under assessment | the root Cargo workspace + the non-Rust trees it carries                                                                      | this document                 |

This is a **container**, not a single product. It is one workspace holding
many independently consumable crates plus non-Rust assets. Treating it as
one shippable artifact is the most common misreading of this repository.

## 2. Measured shape (2026-11-12)

Command: `cargo metadata --no-deps --format-version 1`, parsed in place.

| Metric                                    | Measured                                                                       | Note                                                                                                             |
| ----------------------------------------- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| `workspace_members`                       | **291**                                                                        |                                                                                                                  |
| `packages` returned by `--no-deps`        | **291**                                                                        | equals members, i.e. no path-only non-member packages reported                                                   |
| Members under `crates/`                   | **267**                                                                        |                                                                                                                  |
| Members under `absorption/`               | **20**                                                                         | all under `absorption/PhenoMLX-temp/perf-core/`                                                                  |
| Members under `tools/`                    | **2**                                                                          | `fake-codex-cloud`, `fake-forge`                                                                                 |
| Members under `examples/`                 | **1**                                                                          | `fabric-full-demo` (`examples/full-demo`)                                                                        |
| Members under `native/`                   | **1**                                                                          | `playcua-native`                                                                                                 |
| Crates with **no** in-workspace dependent | **170**                                                                        | counted from the same metadata; these are publication/consumer or deletion candidates, not necessarily dead code |
| Most-depended-on crate                    | `substrate-core` — **36** workspace dependents                                 |                                                                                                                  |
| Next highest                              | `fabric-capability` 15, `engine-spec` 12, `fabric-graph` 12, `focus-domain` 10 |                                                                                                                  |

Per-crate boundaries, paths and dependents are in [`../CRATE-BOUNDARIES.md`](../CRATE-BOUNDARIES.md)
(deliverable D15.2), generated from this same metadata run.

### 2.1 Discrepancy to be aware of

`README.md`'s at-a-glance table states **290** root workspace packages
measured 2026-11-11; the metadata run on 2026-11-12 reports **291**. The
README does not say which package was added, and this dossier does not
assert a cause. Reconciling the two member sets needs a diff of the two
lists, which this pass did not run (see open question 1).

## 3. Absorption history (evidence-backed)

The only absorption visible as _workspace members_ is PhenoMLX: all 20
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

| Area                                               | Claimed count                         |
| -------------------------------------------------- | ------------------------------------- |
| Reusable workflow files under `.github/workflows/` | 90                                    |
| Composite actions under `.github/actions/`         | 6                                     |
| Markdown files under `docs/`                       | 2,668                                 |
| ADRs                                               | 82 in `docs/adr/`, 25 in `docs/adrs/` |
| Registered project manifests                       | 178 (`projects/*.json`)               |

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
is a _map_, not an adoption claim.

| Family                               | Members | What it appears to own                                                                                                                                      |
| ------------------------------------ | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `substrate-*`                        | ~20     | agent-execution substrate: core, app, browser stack, dag, memory, schedule, skills, trace, tui. `substrate-core` is the single most-depended-on crate (36). |
| `driver-*` / `engine-*`              | ~20     | separable driver (argv/cli/http/mcp) and engine (claude/codex/forge/agentapi/a2a/spec/conformance) traits                                                   |
| `fabric-*`                           | ~20     | desktop capture/orchestration fabric: capability, capture, graph, daemon, gui, tray, tui, terminal, web                                                     |
| `focus-*`                            | ~33     | a focus/discipline product line: domain, events, rituals, rules, rewards, penalties, scheduler, ui, sync                                                    |
| `sharecli-*`                         | ~14     | CLI/fleet/mesh/fuse/ipc/sync/session/tray surface over `sharecli`                                                                                           |
| `teamcomm-*`                         | ~6      | team communication protocol, client, daemon, mcp, smoke                                                                                                     |
| `agileplus-*`                        | ~12     | spec-driven development domain: cache, domain, events, git, github, graph, import, nats, triage                                                             |
| `hwledger-*`                         | ~11     | hardware ledger plus a model-explorer search stack (core, index, ingest, rag, skills, tags, server, mcp)                                                    |
| `eyetracker-*`                       | ~8      | eye-tracking: camera, core, domain, ffi, inference, math, cli                                                                                               |
| `pheno-compose-*` / `phenocompose-*` | ~14     | compose-style container/port runtime with port-traits and adapter implementations                                                                           |
| `pine-*`                             | ~6      | a sandbox/syscall-runtime line: core, compat, loader, nvms, syscall                                                                                         |
| `phenotype-*`                        | ~45     | org-wide primitives: errors, config, crypto, observability, retry, rate-limit, ports, tracing, telemetry                                                    |
| `pheno-*` (minus above)              | ~15     | smaller shared utilities (fs, net, shell, i18n, crypto, otel)                                                                                               |
| `absorption/*`                       | 20      | absorbed PhenoMLX perf core                                                                                                                                 |
| `tools/`, `examples/`, `native/`     | 4       | fakes for testing, one demo binary, one native binding                                                                                                      |

## 7. Quality gates

| Gate                                         | State     | Evidence                                                                                                                                      |
| -------------------------------------------- | --------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Coverage floor (85%, docs-3 contract)        | `UNKNOWN` | no coverage artifact was inspected in this pass; `codecov.yml` and `tarpaulin.toml` exist, which indicates an intention, not a measurement    |
| Negative controls / instrument qualification | `UNKNOWN` | not inspected                                                                                                                                 |
| Lint / fmt configuration present             | yes       | `rustfmt.toml`, `clippy` lints in workspace `Cargo.toml` (README), `ruff.toml`, `oxlint.json`, `deny.toml`, `gitleaks.toml`, `trufflehog.yml` |
| Unsafe forbidden                             | `UNKNOWN` | `README.md` states the policy; this pass did not read the workspace `Cargo.toml` lint table for it (open question 5)                          |

A configuration file records an intention; it is not an observed result. A
row above marked `UNKNOWN` stays `UNKNOWN` until a command's output is
recorded beside it.

## 8. Risks

| #   | Risk                                                 | Why it matters                                                                                                                                                                                | Control / next step                                                                                                                   |
| --- | ---------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | **Container-as-product confusion**                   | Consumers may try to build/adopt the whole workspace; it is a container of independently consumable crates                                                                                    | README states the role explicitly; keep it prominent                                                                                  |
| R2  | **Absorbed code at a `-temp` path**                  | `absorption/PhenoMLX-temp/perf-core/*` occupying 20 workspace members implies an unfinished absorption                                                                                        | Decide: promote to `crates/`, or remove from members. Owner `UNKNOWN`                                                                 |
| R3  | **170 of 291 crates have no in-workspace dependent** | Large surface with no internal proof of use; unclear publish intent                                                                                                                           | Classify each as publish / consume-externally / delete; this pass produced the count only, by parsing `cargo metadata` (see appendix) |
| R4  | **README metrics drift**                             | 290 vs 291 packages already diverges within one day                                                                                                                                           | Regenerate the at-a-glance table from a command, with the date in the file                                                            |
| R5  | **Truncated top-level tree**                         | `find . -maxdepth 1` alone shows a very large number of root-level markdown and scratch files (`_*.json`, diagnostic reports, `node_modules`, `target`), which obscures the real entry points | Read `README.md` as the entrypoint; do not infer structure from a root listing                                                        |
| R6  | **No measured build/test state**                     | An unmeasured container of 291 crates can rot silently                                                                                                                                        | Run `cargo check --workspace` on a schedule and record the result here                                                                |

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

| Claim                                               | Command                                                        | Result                                                   |
| --------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------- |
| Workspace member count and paths                    | `cargo metadata --no-deps --format-version 1`                  | 291 members, exit 0                                      |
| Layer distribution                                  | parse of the same JSON                                         | crates 267, absorption 20, tools 2, examples 1, native 1 |
| Crates with zero dependents                         | parse of the same JSON                                         | 170                                                      |
| `docs/dossiers/DOSSIER.md` did not previously exist | `test -f`                                                      | MISSING                                                  |
| No dossier anywhere in-repo                         | `find . -maxdepth 4 -name DOSSIER.md`                          | no output                                                |
| `cmd/dagrun` is a separate Go module                | `head -3 cmd/dagrun/go.mod`                                    | `module github.com/KooshaPari/dagrun`, `go 1.25.0`       |
| Dagrun docs already present                         | `wc -l cmd/dagrun/CONSOLIDATION.md cmd/dagrun/TRACEABILITY.md` | present (see D16.3, D16.4)                               |

---

## 11. Second edition — measurement dated 2026-11-19

This section was added at `f06c3cc7f`. Sections 0-10 above are the 2026-11-12 edition and are kept
intact: their method and their `UNKNOWN`s remain the honest record for that pass. Where this section
supersedes a figure it says so explicitly.

Companion documents written in the same pass:

| Document | Covers |
|---|---|
| `../sessions/2026-11-19-phenoshared-audit/CODEBASE-ATLAS.md` | size, language mix, build topology, structural confusion |
| `../sessions/2026-11-19-phenoshared-audit/QA-MATRIX.md` | 81 workflows, test census, coverage floors, assurance gaps |
| `../atlas/` | the pre-existing governed atlas package, including its generated inventory (stale since 2026-11-07) |
| `../sessions/2026-11-19-phenoshared-audit/CONTAINER-SDK-RESHAPE.md` | the decentralised container SDK plan, built on the measured 355 internal edges |

### 11.1 What changed at 5154a6828 → f06c3cc7f

The only substantive change is a **security remediation commit**: `f06c3cc7f`
"security: remove captured API-key inventory dumps from a public repo (#1124)". It removed 43 files
from the tip (38 process-inventory dumps carrying four credential families plus resume and session
dumps), redacted 6 vendored files in place, and extended `.gitignore`. It did **not** purge history
and did **not** rotate. The disclosure record is
`docs/security/20261117-public-process-inventory-exposure.md`.

Tracked file count rose from 55,940 to 55,898 across that commit, i.e. the tree is otherwise
essentially unchanged.

### 11.2 Corrections to earlier figures

| Figure | First edition | This edition | Why |
|---|---|---|---|
| Workspace packages | 291 (11-12) | **292** (11-19) | re-ran `cargo metadata --no-deps`; one package added |
| Member-list entries | — | 288 | the `members` array holds 288 entries which glob-expand to 292 packages |
| Code lines | not measured | **6,228,356**, of which ≈3.4 M first-party | batch-safe concatenated counting |
| Citations for `docs/absorbed-from-*` | cited, not re-verified | still not individually re-verified | unchanged `UNKNOWN` |
| Build / test state | `UNKNOWN` | still `UNKNOWN` | see 11.3 |

The method lesson is worth recording because it produced a wrong document: `xargs wc -l | tail -1`
returns only the final xargs batch. With 11,466 Rust files that reported 365,543 lines against a
true 3,158,866. Any line count in this repository must concatenate first (`git ls-files -z -- '*.rs'
| xargs -0 cat | wc -l`).

### 11.3 Still unmeasured

`cargo build`, `cargo test`, `cargo check --workspace` and CI results remain `UNKNOWN` for this pass
too. `cargo metadata --no-deps` ran because it resolves no dependencies and starts no compile. A
statement that PhenoShared "builds" still has no source in this document.

### 11.4 The risk that now outranks the rest

Read `docs/security/20261117-public-process-inventory-exposure.md` before any other work on this
repository. Live credentials were committed to a **public** repository, removed from the tip, and
left in history unrotated. Containment order is rotate → update consumers → purge or accept, and all
three are operator actions. An agent must not rotate credentials and must not force-push.

The first edition's risk table (R1 container-as-product confusion … R6 no measured build state) is
unchanged and still valid. The exposure risk sits above all of them.

### 11.5 Fit against the container-SDK requirement

The requirement, in the operator's words, is a "harmonious decentralized CONTAINER SDK so you dont
hae to imkport the entire bulky item".

| Requirement | Present state | Verdict |
|---|---|---|
| Unit separately importable | 292 packages in one root graph; 26 nested sub-workspaces outside it | partial |
| Consumer takes only what it needs | three independent root manifests, no cross-language resolution | no |
| Absorbed material isolated from first-party | absorb residue is a workspace member | no |
| Per-unit versioning | 25 tags total, none observed per package | no |
| Reproducible per-unit build | checked-in `zig-cache`, `.o`, `.rlib`, 1.5 M lines of `.patch` | no |
| Documentation describes units | 11,919 files; markdown ≈ a third of all tracked lines | yes, strongest asset |

The first edition's finding that **170 of 291 crates have no in-workspace dependent** is the most
useful single number for this work: those are the publication candidates that make a container model
real, and they are also the deletion candidates that make it honest.

### 11.6 Reshape plan

Ordered so each phase shrinks blast radius before the next adds surface. Each step has a closure
test an agent can run.

**Phase 0 — contain the exposure.** Operator rotates each value in the disclosure; operator decides
history purge; agent confirms no dump family can be recommitted (`git ls-files` matches none of the
ignored patterns); disclosure doc gains a rotation date per value.

**Phase 1 — make the boundary real.** Split the 292-package workspace into a core workspace plus
opt-in member groups, so a root build compiles core only. Adopt `go.work` over the 47 modules or
declare the per-module order. Register all 26 nested sub-workspaces with an explicit in/out
disposition. Remove `absorption-residue-*` from every member list. Ship a one-line import example
for the three most-used units, verified from a fresh consumer directory.

**Phase 2 — separate first-party from absorbed.** Exclude `absorption/` from first-party gates and
from coverage denominators, printing both denominators separately. Give every absorbed directory a
`PROVENANCE.md`, closing the 3 PENDING and 3 UNKNOWN. Replace plain copies with pinned references
where an upstream still exists. Remove or dereference the `docs/absorbed-from-*` duplicates.

**Phase 3 — shrink what carries no information.** Drop tracked build output (1.5 M `.patch` lines,
213 k `.o`, 419 k `.bundle`, `zig-cache`, `.rlib`), so tracked lines fall by ≈2.1 M and the build
still succeeds. Stop tracking `.vitepress/dist/`. Archive or delete the 841 `triage/pr` and 205
`_sweep` refs down to a documented set. Decide `_archived/` per directory, with no path left
"archived but still built".

**Phase 4 — make assurance attributable.** One coverage-floor policy scoped per first-party
workspace, with no `fail-under 0` remaining. Branch protection committed as data. Every nested
sub-workspace present in a CI job list. The atlas regenerated by script and diffed in CI.

### 11.7 Open questions added by this pass

| Question | Settle with |
|---|---|
| Which of the 81 workflows are required to merge? | `gh api repos/KooshaPari/PhenoShared/branches/main/protection` |
| Are `libs/*` or the 87 Python projects published anywhere? | registry inspection |
| Does each absorbed directory still have a live upstream? | `git remote` per source, or the `PROVENANCE.md` |
| Who outside this repository consumes the 292 packages? | dependency search across org repositories |
| Should the repository stay public? | operator decision; it governs how much history must be purged |

The first edition's open questions 1-5 remain open; question 1 (the 290 vs 291 divergence) is now
answerable as 292 and should be closed on the next revision rather than carried forward.
