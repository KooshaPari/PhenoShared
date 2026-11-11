# SDK catalog

`sdk-catalog.json` is a machine-readable map of every workspace member in this repository: what
layer it occupies, whether it is meant to reach an external consumer, which channel it would ship
on, and what currently blocks it from shipping. It is generated, never hand-written, and a gate
checks it against the publication contract.

```bash
python3 tools/sdk-catalog/generate.py     # writes sdk-catalog.json (~10 s)
python3 tools/sdk-catalog/check.py        # gate; exit 0 = all checked rules hold
python3 tools/sdk-catalog/check.py --rule1        # adds standalone packaging (slow, ~50 s)
python3 tools/sdk-catalog/check.py --rule1-limit 5   # probe packaging on five crates
```

## What it measures

| Field | Meaning |
|---|---|
| `layer` (`L0`-`L4`) | Position in the dependency graph, corrected by a name rule or an annotation |
| `layer_basis` | Which signal decided the layer: `name`, `dag-leaf`, `dag-deep`, `default`, `annotation` |
| `dag_depth` | Longest chain of internal runtime dependencies below the crate |
| `publication_class` | `publish` (meant for an external consumer), `internal`, `quarantine` (no layer evidence, needs curation) |
| `channel` | `crates.io`, or the payload channel for non-Rust surfaces |
| `packaging_ready` | Licence present, not `publish = false`, and no path dependency with an unresolvable version |
| `deps` / `dev_deps` | Internal runtime and dev-only dependency edges |
| `consumers` | Inbound runtime edges from other workspace members |

`annotations.json` holds the exceptions a machine cannot derive, each carrying its reason.

## What the gate enforces

| Rule | Contract |
|---|---|
| R1 | every `publish` crate can `cargo package --no-verify` on its own |
| R2 | no runtime dependency points up a layer (dev-only edges are reported, not failed) |
| R3 | a `publish` crate never enables an L3/L4 crate through a feature |
| R4 | every `publish` crate declares a stability |
| R5 | zero members are unclassified |

## Current state of the repository

Measured 2026-11-10 on the `feat/p0-sdk-catalog` worktree at `f50118b2b`; layer and class counts
re-measured 2026-11-11 after the curation pass, with the gate re-run at the same time.

- **290 workspace members.** All 290 have a layer; none are unclassified and none are
  quarantined. `L0 183 / L1 3 / L2 12 / L3 21 / L4 71`.
- **The workspace is flat.** 218 of 290 members have no internal runtime dependency at all, and
  183 sit at `L0`. Only 67 reach application altitude. Layering is the exception, not the shape:
  most crates are independent packages that share a repository rather than a call graph.
- **48 crates can be published standalone today**, and `cargo package --no-verify` succeeds for
  47 of the 48. The single failure is `phenotype-tooling-observability`, whose manifest points
  `readme` at a path outside the package.
- **Everyone else is blocked, and by one thing.** 105 members carry 238 path dependencies with no
  version requirement (`req = "*"`). `cargo package` refuses those, so no crate that depends on a
  sibling can ship no matter how clean its own manifest is. This is the single highest-leverage
  change available for publication: pinning version requirements unblocks 105 crates at once.
- **Nothing has a 1.0 contract.** All 290 members are `0.x`, so every crate is `experimental` by
  semver. R4 passes on that derivation; no crate claims API stability it has not earned.
- **31 crates are named like a layer they do not occupy.** A name rule assigns L1-L3 while the
  crate has no internal runtime dependency; these are listed in
  `findings.name_rule_above_dag_leaf` so the naming can be corrected rather than the model bent.
- **Non-Rust surfaces are large and mostly untracked as products.** 34 directories carry 1,000+
  lines of Python, Go, TypeScript or JavaScript, 1,056,001 lines in total, of which 689,419 sit in
  14 directories classified as publishable. That count includes 202,628 lines of Python and 71,986
  lines of Go living inside `crates/` itself. None of it can ship as a Rust crate, so all of it
  needs PyPI, Go module and npm channels.
- **No crate is quarantined.** The 25 members that previously had no name rule and no decisive
  dependency position (`agileplus-*`, `eidolon-*`, `focus-*`, `fabric-*`, `substrate-*`) now
  carry an annotation: 27 members in total, each with the edge evidence that chose the layer.
  What made them undecidable is recorded too. `agileplus-github` reads like an `L2` adapter by
  name, but it depends on `agileplus-triage`, so `R2` forces `L3`; that reason is in the file
  rather than in someone's memory. `eidolon-mobile` and `eidolon-sandbox` ship binaries, which
  is the evidence that makes them `L4`. Nothing was deleted, and no layer was assigned without
  a cited edge or artifact.

## Reading a quarantine entry

`quarantine` does not mean "bad" and it does not mean "delete". It means the catalog could not
prove what the crate is, so someone has to say. The fix is an entry in `annotations.json`:

```json
{"members": {"agileplus-cache": {"layer": "L2", "reason": "caches git and GitHub reads"}}}
```

No member is currently in that state, but the class stays in the model: a crate added tomorrow
with no name rule and no decisive dependency position lands in `quarantine` rather than being
silently given an invented layer. The `reason` field is the point of the entry. A layer without
a reason is a guess that outlives the person who made it.
