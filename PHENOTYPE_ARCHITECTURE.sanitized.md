# Phenotype Platform — Cross-Repo Architecture (Sanitized Excerpt)

**This document is a sanitized excerpt.** It is a public-safe subset of an
internal cross-repo architecture reference. The following were removed or
abstracted relative to the source:

- Private repository names — replaced by functional role labels.
- Email addresses, bot handles, and internal hostnames.
- Absolute filesystem paths on operator machines.
- Session identifiers and commit SHAs.
- Git hosting handles, clone URLs, and CLI authentication notes.
- Dated operational worklogs (state snapshots, in-flight branch tables, and
  per-session engineering journals).

The internal source document is unmodified and remains authoritative. Where a
name has been abstracted, the role description preserves the original concern
and its authority boundary, so the governance model is still legible.

**Audience:** anyone returning to the platform after time away, or reviewing
its authority model without access to internal repositories.

---

## The 30-second mental model

The platform is a polyrepo of single-purpose products that together form a
federated agentic system. The newest member — the **fabric substrate** — is a
runtime substrate that makes physical machines, GPUs, OS sessions, and remote
hosts appear as one coherent interactive computer.

**Authority boundaries (do not blur):**

| Concern | Owner (role) | Repository (role label) |
|:--|:--|:--|
| Governed intent (work packages, plans, evidence contracts) | governance layer | governed-intent repo |
| Agent dispatch (task routing, scheduling, dispatch MCP) | dispatch layer | dispatch repo |
| Evidence graph (DAG, atomic claim/lease, presets) | evidence graph | evidence-graph repo |
| Process supervision (runtime-process, FUSE driver, sharing) | process supervision | process-supervision repo |
| **Physical execution substrate (capability inventory, routes, RT surface)** | **fabric substrate** | **fabric-substrate repo** |
| Session history | session history | session-history repo |
| Allocation / economics | allocation ledger | (own repo TBD) |
| Source provenance / research experiments | research ledger | research-ledger repo |
| Repo metadata | repo metadata | repo-metadata repo |
| Hardware inventory | hardware ledger | hardware-ledger repo |
| VCS lineage (VCS bridge) | VCS lineage | vcs-lineage repo |
| VCS version + control plane | version control plane | version-control repo |
| Fleet operations (signing, packaging, distribution) | fleet ops | fleet-ops repo |
| Web UI shell | apps | apps repo |
| User journey research | journeys | journeys repo |
| Traceability / dependency map | traceability spine | traceability-spine repo |
| Go SDK | go sdk | go-sdk repo |
| Python SDK | python sdk | python-sdk repo |
| Component registry | registry | registry repo |
| Hub / service mesh | hub | hub repo |
| MLX gateway (Apple MLX) | mlx gateway | mlx-gateway repo |
| Vector index / search | vector search | vector-search repo |
| MCP servers (dispatch MCP, etc.) | MCP servers | mcp-servers repo |
| Observability (traces, metrics) | observability | observability repo |
| CI / lint / tooling | tooling | tooling repos |
| Pluggable traits | plugins | plugins repo |
| Worktree manifest | tooling + worktrees | worktrees tree |
| Archive (historical snapshot) | archive | archive repo |
| Security / provenance | security lane | security repo |
| VR / spatial | spatial lane | spatial repo |
| Spreadsheet / CAD | extensions | extensions repo |
| Local ops daemon | local ops | local-ops repos |
| Runtime configuration | runtime config | runtime-config repo |
| Misc (tokens, viz, etc.) | various | various repos |

**Archived / read-only:**

| Repository (role) | Status | Migration |
|:--|:--|:--|
| legacy DAG repo | ARCHIVED → evidence graph + governance layer | DAG/queue/atomic-claim → evidence graph; PM/cockpit → governance layer |
| process supervision (historical) | active in 1.0.0 | wave plans retained in the process-supervision repo |

---

## Key cross-cutting relationships

### Fabric substrate ↔ low-level inventory adapter

The fabric substrate subsumes the low-level adapter's runtime inventory
mission. ADR-0020 ("provisional name") is intentionally unresolved. The
migration plan: keep the adapter as a low-level library for resource /
process / network inventory; the fabric substrate wraps it with a graph-native
topology and route planner. **Do not** rename the adapter until PF-WP-010
ships a working capability descriptor.

### Fabric substrate ↔ process supervision

The fabric substrate accepts a `TaskSpec` describing a *process* with
input/output surfaces. The process-supervision lane already has FUSE-driven
file system sharing and process supervision. The integration is via event
contracts (see `<fabric-substrate>/ecosystem/event-contracts.json`). Process
supervision stays the implementation authority for process management; the
fabric substrate's routes and surfaces are orthogonal.

### Fabric substrate ↔ governance layer

The fabric substrate is *governed by* the governance layer. The specs in
`<fabric-substrate>/specs/001..012/` are shaped as governance-layer feature
specs (meta.json + spec.md + plan.md + tasks.md). The first vertical slice
(PF-WP-000/010) will produce a spec, plan, and tasks in the same shape and
register them as a work package under the governance layer.

### Fabric substrate ↔ dispatch layer

The fabric substrate accepts a `TaskSpec` from the dispatch layer. Dispatch
stays the dispatch authority; the fabric substrate provides the route /
surface / capability binding that the TaskSpec's requirements resolve to. No
shared database; integration is via the event-contracts schema.

### Fabric substrate ↔ evidence graph / session history

The fabric substrate emits evidence references (claim ids, route ids,
capability ids). The evidence graph owns the evidence graph; the
session-history store owns the time-ordered session log. The fabric substrate
does not write to either directly — it produces references and lets the
evidence graph and session-history store index them.

### Fleet ops ↔ fabric substrate

Fleet ops owns fleet operations (signing, packaging, distribution, telemetry
collection). The fabric substrate owns product packaging. The boundary is
`<fabric-substrate>/work/release-plan.md` ↔ `<fleet-ops repo>/`.

---

## Branch naming convention

- `feat/<topic>-<yyyymmddThhmmssZ>` — feature branches from main
- `fix/<topic>-<yyyymmddThhmmssZ>` — bug fix branches
- `chore/<topic>-<yyyymmddThhmmssZ>` — tool / CI / non-behavior
- `docs/<topic>-<yyyymmddThhmmssZ>` — doc-only branches
- `release/vX.Y.Z` — release branches
- `worktree/<topic>-<yyyymmddThhmmssZ>` — worktree manifests

## Worktree convention

`worktrees/<owner>/<topic>-<yyyymmddThhmmssZ>/` is the canonical worktree
path. See `worktrees/INDEX.md` for active worktrees.

---

## Not included in this excerpt

The source document also carries dated operational material that was
intentionally omitted: repository state snapshots, in-flight branch and dirty
worktree tables, open-thread trackers, and per-session engineering journals.
Those sections are point-in-time operational records rather than durable
architecture, and they are the sections that carried the removed identifiers
(session UUIDs, commit SHAs, host paths, and handles).

Also omitted: the internal coordination notes (chat-bot auto-commit behavior,
signing-wave ownership, and metaproject conventions) and the internal
onboarding walkthrough with its reading order. Both remain in the source
document for internal readers.
