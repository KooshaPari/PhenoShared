# PhenoShared as a container SDK

**Operator intent, verbatim:** *"harmonious decentralized CONTAINER SDK so you dont hae to imkport
the entire bulky item."*

This document is the reshape plan. It is built only from figures measured on 2026-11-19 at
`f06c3cc7f`, on the Mac worktree and re-derived on `ssh desk` (WSL2 Fedora) from a fresh clone of the
same SHA. Where a number is carried forward rather than re-measured, it says so.

---

## 1. What the measurement actually says

The decisive figure is not the size. It is the edge count.

| Measurement | Value | Host |
|---|---|---|
| Workspace packages | 292 | desk, `cargo metadata --no-deps` |
| **Intra-workspace dependency edges, as declared** | **355** | desk, reverse graph over `dependencies` |
| Packages with **zero** in-workspace dependents | **170** | desk |
| — of which lib-only | 84 | desk |
| — of which lib + bin | 24 | desk |
| — of which bin-only | 28 | desk |
| Packages with any lib target | 263 | desk |
| Binary targets | 68 | desk |
| Nested cargo sub-workspaces outside the root graph | 26 | Mac lane |
| Go modules / `go.work` | 47 / **0** | both hosts agree |

**355 declared internal edges over 292 packages is 1.2 edges per package.** A codebase that were one
system would show an edge count of the same order as its package count times a few. This one is close
to a set of independent artifacts that happen to share a directory, a workspace file, and one version
number. 170 of 292 packages have nothing inside the repository that depends on them.

So the "bulky item" is not bulky because the code is intertwined. It is bulky because **publication
is monolithic**: there is exactly one thing to import, and it is the whole repository. The
decentralisation work is therefore mostly *packaging and release*, not refactoring.

## 2. What a container is, here

A container is the unit a consumer imports. Today the unit is the repository. The definition proposed:

A container is a set of crates that (a) has a stable public API surface, (b) has no in-workspace
**reverse** dependency that forces it to move with the rest of the tree, (c) declares its own version
and changelog, and (d) can be consumed without cloning this repository.

The boundary test is mechanical, not aesthetic:

```bash
# candidate if and only if this prints 0
cargo metadata --no-deps --format-version 1 | python3 -c '
import json,sys
m=json.load(sys.stdin); names={p["name"] for p in m["packages"]}
print(sum(1 for p in m["packages"] for d in p.get("dependencies",[]) if d.get("name")==sys.argv[1]))' crate_name
```

That test yields 170 candidates. It is a necessary condition, not a sufficient one: a crate nobody
depends on may also be a crate nobody wants. Selection is a product decision; the test only removes
the ones that structurally cannot be split.

## 3. Three tiers, because 170 containers is not a plan

| Tier | Population | What it is | Ships as |
|---|---|---|---|
| **T0 — facade** | 1 | a feature-gated umbrella crate | one import line, `phenoshared` |
| **T1 — core containers** | from the 84 lib-only zero-dependent crates, curated | the actual reusable substance | individually versioned library crates |
| **T2 — satellites** | the 28 bin-only, plus the 68 binary targets | CLIs, daemons, tools | container images / prebuilt binaries |

T0 is what answers the operator's sentence directly and it is cheap: a facade with one optional
dependency per container, all default-off. A consumer writes `phenoshared = { version = "1", features
= ["graph"] }` and Cargo's own feature resolution means the binary carries `graph` and not the other
169. Nothing moves, nothing splits, and the bulky import is gone on day one.

T1 is the decentralisation proper: independent semver, independent release cadence.

T2 is where the "container" word earns itself literally: 68 binary targets and 81 Dockerfiles already
exist, so packaging is not greenfield.

## 4. What makes it harmonious rather than 170 snowflakes

Five mechanisms, each of which has a precedent already inside this repository:

1. **A machine-readable catalog.** One generated index listing every container, its version, its
   published digest, and its declared dependents. Precedent: `docs/atlas/MANIFEST.json` pins 257
   payloads by sha256 and is validated nightly. Same shape, different subject.
2. **Generated, never hand-written.** The catalog is produced from `cargo metadata` in CI. The atlas
   package's own failure mode is instructive: its `codebase/INVENTORY.md` was last regenerated
   2026-11-07 and now reports 81 members against 292, and its nightly validator has been red for 30
   consecutive runs. A hand-maintained inventory rots; a generated one cannot.
3. **One contract per container, not one per repo.** Each container declares its API stability tier
   and its minimum supported consumer. Consumers pin containers, never the repository.
4. **Registry publication, not path dependencies.** The moment a consumer outside this repo uses a
   container, path deps must not leak. This is the real test of whether decentralisation happened.
5. **The facade is generated from the catalog**, so adding a container is one catalog entry plus one
   manifest line. If it takes more than that, the shape is wrong.

## 5. Phased plan, each phase with its own acceptance test

| Phase | Work | Acceptance test |
|---|---|---|
| P0 | generate the catalog from `cargo metadata` in CI | catalog lists 292 packages / 355 edges / 170 zero-dependent; CI fails if it drifts from a live `cargo metadata` |
| P1 | publish the T0 facade with all features off by default | an external scratch crate depends on `phenoshared` with one feature and its `Cargo.lock` pulls only the containers that feature needs |
| P2 | publish the curated T1 set | an external crate consumes one container from the registry, with no path deps and no git deps |
| P3 | build T2 satellites from the existing 68 bins / 81 Dockerfiles | one satellite image built and run from CI, not from a developer machine |
| P4 | decentralise the release | a second container releases while the first stays fixed, proving cadence is independent |

P1 is where "you don't have to import the entire bulky item" becomes true and demonstrable. P4 is
where "decentralized" becomes true. Everything before P4 is packaging.

## 6. Risks this plan inherits, named

| Risk | Evidence | Consequence for the reshape |
|---|---|---|
| Dependency vulnerability load | GitHub reports **405 vulnerabilities on the default branch, 12 critical** (2026-11-19) | a container inherits whatever it pulls; without per-container audits, decentralisation multiplies the exposure instead of containing it |
| 26 nested sub-workspaces outside the root graph | Mac lane, 2026-11-19 | they cannot be published by a root-graph mechanism; each needs its own decision |
| 47 Go modules with no `go.work` | both hosts | Go containers need a different mechanism entirely, or they stay outside the SDK |
| Governance drift | stale `INVENTORY.md`, 30/30 red nightlies | a generated catalog with a CI drift check is a requirement, not a nicety |
| Docs and schema outweigh code | 2,007,094 lines Markdown, 1,082,522 lines JSON vs 3,158,866 Rust (desk) | a container has to ship documentation and schema; that is the larger half of the tree by line count |

## 7. What this document does not decide

Naming, licensing per container, whether any container becomes its own repository, and which of the
84 lib-only candidates are worth curating into T1. Those are product decisions and belong to the
operator. This document only fixes the boundary test, the tiers, the mechanisms, and the order.

One judgement is offered anyway: **do T0 before anything else.** It is the only phase whose output
the operator can feel immediately, it requires no repository splitting, and it makes the rest of the
plan measurable against a working alternative rather than against a diagram.
