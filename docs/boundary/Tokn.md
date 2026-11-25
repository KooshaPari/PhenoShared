---
repo: "Tokn"
role: token-cost-ledger-and-routing
status: active
last_boundary_review: 2026-07-26
review_cadence: 30d
in_scope:
  - Token and provider cost/usage accounting
  - Pareto routing substrate consumed by OmniRoute
out_of_scope:
  - Session capture, archive, and replay (SessionLedger)
  - Generic organization registry/governance records (phenotype-registry)
---

# Boundary — Tokn

## In Scope

TokenLedger runtime and its `tokenledger::routing` Rust substrate.

## Out of Scope

| Not here | Lives in | Reason |
| -------- | -------- | ------ |
| Session capture/replay | SessionLedger | Distinct continuity/session-artifact domain |
| Registry provenance and boundary evidence | phenotype-registry | Governance metadata only; no runtime absorption |

## Boundary Crossings

| Crossing | Direction | Surface | Status |
| -------- | --------- | ------- | ------ |
| Routing intelligence | Tokn -> OmniRoute | Rust `tokenledger::routing` | green |

## Last Boundary Review

**Date:** 2026-07-26
**Reviewer:** boundary audit agent
**Worklog / finding:** `registry/audit-absorption-justification/tokn-boundary-20260726.json`
**Decision:** Keep canonical standalone. Existing `TOO_LARGE_RETIRE`/archive-only index entry is stale and contradicted by the active public remote and OmniRoute consumer relationship.

**Next review:** 2026-08-26
