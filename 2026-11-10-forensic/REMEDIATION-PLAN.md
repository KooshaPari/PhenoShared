# Decentralized container SDK — target shape and remediation (v2)

Repo: `KooshaPari/PhenoShared` · measured 2026-11-10 · supersedes v1 of this file.
Every figure is from the evidence lanes in this directory. Anything not measured is marked **UNKNOWN**.

**What changed in v2.** v1 assumed a single SDK with an eviction programme ("attic", evict duplicate
families). That was the wrong target. The intended shape is a **decentralized container SDK**: the
container stays the home for bulky and non-publishable material, and *consumability* is a property
declared per crate — so a consumer takes one slice and never imports the bulk. Decentralized here
means **no meta-crate and no single import root**; it does not mean splitting the repo.

That distinction retires most of v1. Nothing is evicted to make the shape look clean. Things are
**classified**, and the classification is enforced by a test a consumer can run.

---

## 1. The three identity statements are reconcilable — and were never actually in conflict

| Source | Claim | Under v2 |
|---|---|---|
| `README.md:3` | "a container repository, not a single-purpose project" | **True and retained.** Container = home for bulky + non-publishable payload. |
| `PRD.md:3` | "each crate independently consumable" | **True and retained.** This is the SDK half. |
| `PRD.md:3` (same line) | "no inter-crate dependencies" | **False, and should be struck.** The substrate spine has a real chain (`core → app → adapters → drivers`) enforced by `arch-test`. Independence is per *publication unit*, not per *dependency graph*. |
| `ADR-ECO-014` | "decompose — no generic consolidation repo" | **Half-retained.** A generic consolidation repo with no contract is the failure mode. With a seam contract (below), consolidation is what makes decentralization affordable. The ADR should be amended rather than obeyed. |

So the identity line becomes one sentence with two clauses, not two competing ones:

> PhenoShared is the container where Phenotype's bulky and non-publishable material lives, and it
> publishes a curated subset of crates that are each independently consumable without the container.

The whole plan is about making the second clause mechanically true. It currently is not: nothing is
published, and a crate that inherits `[workspace.package]` fields and uses `path` dependencies cannot
be taken standalone today.

---

## 2. The two axes: publication class × layer

Every crate gets one cell. That is the entire classification, and it replaces both "which family does
this belong to" and "what do we evict".

**Axis 1 — publication class** (the decentralization switch):

| Class | Meaning | Obligation |
|---|---|---|
| `publish` | Part of the consumable surface | semver, docs, doctests, **standalone `cargo package` must succeed**, no undeclared path deps |
| `internal` | Built and tested in-container, never published | none beyond build + test |
| `quarantine` | Exists, builds maybe, not trusted | must carry a reason string and a target class; may not be depended on by `publish` crates |

**Axis 2 — layer** (the shape):

```
L0  core-*      pure primitives, no I/O, no async runtime
L1  port-*      trait contracts only, zero impls
L2  adapter-*   impls of L1  (store-, http-, mcp-, redis-, cloud-, driver-)
L3  engine-*    domain services, planners, orchestrators
L4  app-*       daemons, CLIs, TUIs, GUIs  → always `internal`
```

Rules: edges point downward only; a `publish` crate may not depend on an `internal` or `quarantine`
crate; L0 has no L1+ dependency; L4 is never published.

Everything in this table lives in one generated file, `sdk-catalog.json`, produced from
`cargo metadata` plus per-crate annotations. Nothing human-facing is hand-written from it.

---

## 3. The seam contract — what "harmonious" means when it is testable

Five rules. Each is one command, and each currently fails for most crates.

| # | Rule | The check | Why it matters |
|---|---|---|---|
| 1 | **Standalone packaging** | `cargo package --no-verify` succeeds for every `publish` crate | Directly proves "you don't have to import the bulky item". Today almost certainly fails: `path` deps and `[workspace.package]` inheritance do not survive packaging without explicit `version`/`license` fields |
| 2 | **Layer discipline** | workspace-wide arch test, not just the `substrate-*` family | Turns "decompositional" from a claim into an invariant |
| 3 | **No bulk-leaking features** | each `publish` crate's default features pull only downward, never an `L3`/`L4` crate | A feature flag that drags the runtime in is a bulk import with extra steps |
| 4 | **Declared stability** | every `publish` crate states a stability level (`experimental` / `stable` / `frozen`) | A consumer cannot pick a slice without knowing which slices move |
| 5 | **Catalog completeness** | `sdk-catalog.json` covers 100% of workspace members, with zero `unclassified` | Prevents a new crate arriving unclassified, which is how 13 absorption trees stayed invisible |

Rule 1 is the load-bearing one. If a crate cannot `cargo package`, it is not consumable, no matter
what the README says — and that is the exact gap between "monorepo that compiles" and "SDK".

---

## 4. What genuinely cannot be one item — and should not try

You said some things are just not possible as one item. These are the cases, and each gets its own
publication path rather than a forced Rust crate:

| Payload | Why it cannot be a Rust crate | Correct home |
|---|---|---|
| Python (~52% of code LOC: `agents/`, `servers/`, `python/`) | different runtime and distribution model | Python package(s), own index; container holds source |
| Go (~18%: `go-fabric/`, `linux-client/`, `windows-client/`, `native/`) | Go modules, not cargo | Go module(s), own proxy; container holds source |
| TS/TSX/JS (`sites/`, `web/`, `dashboard/`) | browser/node distribution | npm package(s) |
| `crates/fabric-gui/src-tauri` | binds GTK/WebKit/libsoup-3.0; already workspace-excluded | desktop release artifact, not crates.io |
| `crates/fabric-frame-transport/fuzz`, `crates/forge_daemon` | also workspace-excluded, so the root build never sees them | own gate, or explicitly `internal` with a documented escape |
| Platform clients (`linux-client`, `windows-client`) | platform-specific binaries | release artifacts |
| `.vendor/lancedb` | third-party vendored tree | stays vendored, excluded from metrics |

This is what "decentralized" has to mean in practice: a **multi-ecosystem publication matrix**, where
cargo is one channel, not the only one. The container is the only place that can hold all of them at
once, which is why the container is correct and a single crate is not.

---

## 5. Phases (v2)

Unchanged in P0, P1, P5, P6. P2 is extended, P3 is replaced, P7 is expanded, P8 unchanged.

### P0 — Baseline (still blocks everything)
`cargo check --workspace --all-targets` + `cargo test --workspace` at a named SHA, on the desk node
(`~/bin/rbuild`). Commit `sdk-catalog.json` from `cargo metadata --no-deps`. Last known build state:
PASS with 47 warnings at `main @ 1056f3e8`, 2026-09-16, before the workspace grew from 76 to 283
declared members.
**Exit:** one recorded build result; catalog committed; the 76 / 283 / 372 / 178 count question closed.

### P1 — One identity, generated numbers (unchanged, still cheapest)
Write the two-clause identity sentence; strike the false "no inter-crate dependencies" line; amend
ADR-ECO-014; relocate the 128 foreign-provenance root `.md` files; regenerate README figures from the
catalog; fix the stale `[workspace.package] repository` and the `Taskfile.yml` `ci` target that calls a
non-existent `scripts/ci-local.sh`.
**Exit:** properties 1 and 2 green; R-01, R-05, R-06, R-07, R-08 closed.

### P2 — Classify every crate, then enforce (extended)
Assign each of the 283 members a `(class, layer, stability)` triple. Unassignable goes to `quarantine`
**with a reason**, never to a silent default. Generalize `arch-test` from the `substrate-*` family to
all members.
**Exit:** catalog covers 100% of members with zero `unclassified`; arch test runs on the PR path.

### P3 — Deduplicate concepts, do not evict payload (replaces v1 P3)
The v1 "collapse and evict" programme is retired. What remains is genuine concept duplication, where
two crates claim the same concept and neither is marked canonical:

- AgilePlus exists three times (23 + 51 + 25 dirs) and **no ADR says which is real**. Pick one as
  canonical, mark the other two `quarantine` with a reason. Do not delete: the container is allowed
  to hold them, it is not allowed to leave all three looking live.
- `pheno-compose` / `pheno-compose-port` / `absorption/pheno-forge` = three homes, one concept: same
  treatment.
- Remove the 4 nested `X/X` duplicate manifests — that is a workspace-flattening bug, not payload.
- One naming rule (`pheno-<domain>-<layer>`) with a rename map; aliases deprecated forward-only.
**Exit:** every duplicated concept has exactly one `publish` or `internal` canonical and the rest
`quarantine` with a reason; LOC overstatement 2.2× → ≤1.05×.

### P4 — Absorption ledger (retargeted: classification, not relocation)
All 14 trees get a state, not a move: `staged` (in container, not wired, has a named promotion owner),
`landed` (wired + tested), `archived` (kept, explicitly never built), `dead` (manifest retained).
13 of 14 are currently unwired (48 MB) with no state at all. Also: make `docs/absorbed-from-<X>` and
`absorption/<X>` correspond 1:1 — their mismatch is the mechanism that hid those trees. Close
`agent-user-status` as a recorded permanent loss rather than a pending task.
**Exit:** zero trees in no state; ledger check green in CI.

### P5 — Land the unfinished work (unchanged; you confirmed yes)
18 `wrapup/*-20261108` branches, all unmerged, 1–498 commits ahead, plus `integration/absorbed-20261109`.
Triage each: merge, supersede, or tag-and-delete.
**Exit:** 0 unmerged wrapup branches; local branches at a declared ceiling (28 today, 28 worktrees).

### P6 — Quality that fails a merge (unchanged)
Root-manifest `cargo-deny` on the PR path; remove `continue-on-error` from `ci.yml` and
`license-compliance.yml`; coverage floor 36 → 52 (a ratchet *below* measured 54.79, never above);
wire the PII sweep and cosign or delete them; query branch protection; fix the 50 manifests that
declare no license at all (323 correctly inherit via `license.workspace`, 317 declare explicitly —
a literal `^license =` grep misreports all 323).
**Exit:** every `PASS` in the QA matrix traces to a workflow that fails on push/PR; 0 FAIL controls.

### P7 — Publication matrix (expanded; crates.io confirmed)
Rust channel: version scheme, per-crate semver via release-plz, declared MSRV, feature-flag matrix,
changelog, `cargo package` green for every `publish` crate, then publish L0–L2 to **crates.io** and
tag. Non-Rust channels: name the Python, Go, and npm publication units (or declare them
container-only, explicitly). Every channel gets a tag; today all 9 tags are housekeeping or
`promptscrape-*`, and **0 are release tags**.
**Exit:** one tagged release per declared channel; one real downstream consumer pinned to a version
rather than a branch or SHA.

### P8 — Runtime unification (unchanged)
One host, one catalog; drivers resolve adapters by capability name rather than member ordering (a live
risk: `absorption/PhenoMLX-temp/perf-core/*` is a member with 38 refs competing with `crates/` engine
and focus families). Single-source the `phenotype-daemon` port constant (`9456` in `main.rs` vs `8953`
in `protocol.rs:186`).
**Exit:** one daemon, one catalog, adapters runtime-selectable, no duplicated constants.

---

## 6. Minimum viable maturity — now five moves

1. **P0** — build baseline + committed catalog. Nothing else is knowable.
2. **P1** — one identity sentence + generated numbers. Removes the agent-poisoning vector.
3. **P2** — classify every crate + workspace arch test. This is the (class, layer, stability) triple.
4. **Seam rule 1** — `cargo package` green for the crates you intend to publish. This single check is
   what distinguishes "container" from "container SDK".
5. **P7 (Rust channel only)** — one tagged, resolvable crates.io release.

P4 is the disease-prevention move: without the ledger, the 13 dangling trees regrow.

---

## 7. Open items and classification decisions

### 7.1 The four classification calls (recon complete)

You asked me to go through these rather than decide blind. Done, read-only, with the numbers below.
Note that **nothing here is evicted for shape** — the last column is the class, per §2.

| Item | What it actually is | Measured | Class |
|---|---|---|---|
| `crates/focus-*` | **FocalPoint**, a complete productivity product: its own DSL (`focus-lang` / `focus-ir`, Starlark→IR compiler), rules engine, scheduler, coaching, rewards/penalties, plugin SDK, 7 `[[bin]]` entrypoints | **43 crates**, 43,601 `src/` LOC, 25 explicit members; arrived in ONE commit `19f8e0ebe` (2026-09-16, "extract 53 crates from FocalPoint"); 53 = 43 focus + 9 connector | **`internal`** (product surface, not core). No `phenotype-*`/`substrate-*`/`fabric-*` crate depends on any `focus-*`; only its own 9 `connector-*` do |
| `crates/sharecli*` | Real Rust, not a stub: 575 files / **119,855 LOC** (all `.rs` in the 12 crates), `src/`+`tests/`+`benches/`, 12 crates, all workspace members | **`~/CodeProjects/sharecli` does not exist**, and the family has no provenance file, so there is no upstream to reconcile against | **`internal`, publish later** — unconsumed (its one cross-family consumer, `crates/harness-native`, is not a workspace member), but 120k LOC with no upstream and no recorded history is unrecoverable if dropped |
| `absorption/PhenoInfra/` | 2,532 files / 28 MB, but only **157 `.rs`** — its Rust was already extracted into `crates/`; this is the residue (766 md, 293 json, 205 go, 163 yml) | **0 workspace refs**; provenance pinned: `ecf486cab`, absorbed 2026-09-27, source repo archived | **`archived`** — and because the SHA is pinned, the tree is reproducible from `KooshaPari/PhenoInfra`; it is the one tree where dropping payload is safe |
| `docs/absorbed-from-PhenoTooling/` | The real 70 MB payload (8,257 files, mostly JS + docs). `absorption/PhenoTooling/` **does not exist**; `docs/absorbed-from-zz-zz-agentcheck-PhenoTooling/` is a 4 KB pointer | **0 workspace refs**, and `ABSORPTION.md` records the repo name but **no commit revision** | **`archived` — but block on provenance**: unlike PhenoInfra, no SHA is pinned, so payload must not be dropped until the manifest is completed |

One shared finding: `focus-*` is the **largest absorption in the repo with no absorption record at all** — no `docs/absorbed-from-FocalPoint`, nothing in `docs/ABSORPTION_INDEX.md`. That is the precise failure the P4 ledger gate exists to prevent, and it is live today, not hypothetical.

Disk hazard: **none** in any of the four. No nested `.git`, `target`, `.cargo-target` or `node_modules`; every size above is source-only.

### 7.2 Settled

- **Publish target:** crates.io (Rust channel). Confirmed.
- **Wrapup branches:** wanted → P5 lands them rather than closing them.
- **Attic:** dropped. It was a v1 term for a relocation zone; classification replaces relocation, so
  the concept is not needed and does not appear in v2.
- **Eviction:** retired as a shape tool. Only `archived` with a pinned SHA is a delete candidate, and
  that is a disk decision, not an architecture one.

### 7.3 Caveat that affects reproducibility

This working tree is being **mutated by another process while the analysis runs**. Observed directly:
`9 staged deletions` of `crates/phenotype-dag-core/*`, the matching member removed from the root
`Cargo.toml`, and `cmd/dagrun/internal/plan/dagschema_test.go` modified. Consequence: the 283-member
count is a point-in-time measurement and was 282 in the tree at the moment of this check. Structural
counts held across the run; member-level counts drift. That is also the argument for P0's committed
`catalog.json`: a live count on a mutating tree is not a specification.
