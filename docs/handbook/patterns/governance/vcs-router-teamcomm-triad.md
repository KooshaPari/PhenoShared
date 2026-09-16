# VCS / Router / TeamComm Triad

**Last refreshed:** 2026-09-09 (PT)
**Audience:** contributors to any of the three repos; consumers in `phenotype-router`, `PhenoVCS`, or `phenotype-teamcomm`.
**Status:** proposed (no operator accept yet for any absorb / merge decision).

## Purpose

Three repositories form a *team-coordination-over-git* stack. They are intentionally separate (different language surfaces, different deployment targets, different test environments) but each is load-bearing for the others. This document captures the dependency graph so contributors don't accidentally break a downstream consumer.

## The three repos

| Repo | Language | Default surface | Purpose (verbatim where possible) | Status |
|---|---|---|---|---|
| [`KooshaPari/PhenoVCS`](https://github.com/KooshaPari/PhenoVCS) | Rust | CLI + library | Phenotype-version-control layer — worktrees, branch topology, deterministic commit identities over the Git object model. Substrate of the other two. | active (last push 2026-09-10) |
| [`KooshaPari/phenotype-router`](https://github.com/KooshaPari/phenotype-router) | Rust | library | Routes messages across git workspaces; depends on PhenoVCS for identity. | active (last push 2026-09-09) |
| [`KooshaPari/phenotype-teamcomm`](https://github.com/KooshaPari/phenotype-teamcomm) | Rust | library | Human-team communication patterns on top of PhenoVCS and phenotype-router. | active (last push 2026-09-10) |

All three live on the KooshaPari GitHub account under the Phenotype-org umbrella. None is archived. None is private.

## Dependency graph

```
              ┌─────────────────────┐
              │  PhenoVCS           │  substrate
              │  (worktrees, commit │
              │  topology, identity)│
              └──────────┬──────────┘
                         │ provides identity
              ┌──────────▼──────────┐
              │  phenotype-router   │  message routing
              │  (workspace-aware  │
              │  dispatch)          │
              └──────────┬──────────┘
                         │ provides topology
              ┌──────────▼──────────┐
              │  phenotype-teamcomm │  team patterns
              │  (multi-agent coord)│
              └─────────────────────┘
```

`phenotype-router` imports `PhenoVCS` types (`WorktreeID`, `CommitTopology`) for routing decisions. `phenotype-teamcomm` imports `phenotype-router` for topology-aware message construction *and* imports `PhenoVCS` types directly for identity. There is **no reverse dependency** — `PhenoVCS` does not know about the other two.

## Versioning contract

The three repos share a `[workspace-deps]` style convention. Until a registry-grade contract exists:

1. **Patch + minor versions are compatible within a release line.** A bump from `0.3.x` to `0.3.y` must not break identity or routing interfaces.
2. **Major bumps require a coordinated PR per repo.** The team must land all three in the same week or none.
3. **Branch names should encode the contract** (`router/v0.4-identity-bump`, `teamcomm/v0.4-identity-bump`).

## Test matrix

Each repo has its own test surface; the triad-level tests live where the dependency is consumed:

| Consumer | What it tests | Where |
|---|---|---|
| `PhenoVCS` | Worktree identity, commit topology, deterministic-hash invariants | `PhenoVCS/tests/` |
| `phenotype-router` | Workspace-aware dispatch given a PhenoVCS identity | `phenotype-router/tests/` |
| `phenotype-teamcomm` | Multi-agent coordination patterns through the router | `phenotype-teamcomm/tests/` |

Triad-level integration tests would live in a *fourth* repo (no such repo exists yet — see "Open questions" below).

## Open questions (operator-decision pending)

1. **No triad-level integration tests.** Each repo tests its own contract; the cross-repo invariants are not asserted anywhere. Either (a) add a `phenotype-triad-tests/` repo that pulls all three as git deps, or (b) accept the risk and document the gap here.
2. **`PhenoVCS` vs `phenotype-router` shared `substrate` dependency.** Both depend on `substrate` (the Rust MCP driver crate). If either changes its substrate version, the other may need to follow. Document or automate.
3. **Should `phenotype-teamcomm` move into a "coordination" workspace that includes `phenotype-router`?** The two are the most coupled. Per AGENTS.md, *migration / absorption / decomposition applies only when supported by the repository's agreed role and evidence*. No operator-accepted decision exists yet.
4. **`phenoForge` is also a task-orchestration repo.** Description overlap with `phenotype-router` exists. Either (a) clarify scope boundaries, (b) consolidate, (c) leave separate. **Visibly proposed; not decided.**

## Why this is a triad and not one repo

Three reasons:

1. **Different deployment targets.** `PhenoVCS` runs in a single workspace; `phenotype-router` runs per-team across many workspaces; `phenotype-teamcomm` runs per-team-per-agent. Co-locating them forces one binary to handle three operational shapes.
2. **Different upgrade cadence.** Identity invariants (`PhenoVCS`) change rarely; routing rules change often; team patterns change weekly. Co-locating forces all three to ship at the lowest common cadence.
3. **Different consumer surfaces.** A consumer that needs only identity should not be forced to pull routing or teamcomm code. Splitting keeps the dependency surface small.

## When this triad SHOULD be consolidated

Consolidate the three into one repo *only* if at least two of these become true:

- The same consumer fleet imports all three.
- A registry-grade version contract makes the cross-repo invariants testable from a single checkout.
- The team consistently ships all three at the same cadence.

**None of these are true today.** Per the EXECUTION-CORRECTION rule, the absorb decision is operator-bound — this document records the current state and the conditions under which the decision should be revisited.

## File locations

- `KooshaPari/PhenoVCS` — primary
- `KooshaPari/phenotype-router` — primary
- `KooshaPari/phenotype-teamcomm` — primary
- `KooshaPari/phenodocs` — this document and `mcp-fork-selection.md` are siblings under `docs/handbook/patterns/governance/`

## Out-of-scope (separate batches)

- The BLOCK A app trio (DataKit + Stashly → Apisync absorb) — operator decision pending.
- Observability consolidation (pheno-tracing + Logify → PhenoObservability) — operator decision pending.
- Any actual code change to PhenoVCS, phenotype-router, or phenotype-teamcomm — this is a docs-only PR.
