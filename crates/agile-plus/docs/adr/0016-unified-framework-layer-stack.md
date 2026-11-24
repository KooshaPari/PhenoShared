# ADR-0016: Unified Framework Layer Stack

## Status

Proposed

## Context

[`FRAMEWORK_ANALYSIS.md`](../harmonization/FRAMEWORK_ANALYSIS.md) §4.3 recommends a five-layer
stack (L0 Evidence through L4 Outcomes) composing OKRs, Shape Up, BMAD, GSD, Spec Kitty,
OpenSpec, Spec-Kit, Scrum, and Waterfall RTM vocabulary — without adopting any single
framework wholesale.

The harmonization track must decide **which layer owns which runtime** after Tracera embeds
AgilePlus, and how external frameworks map to layers.

## Decision

1. **Adopt the five-layer model** as the organizing principle for all PM tooling in the
   Phenotype stack:

   | Layer | Purpose | Primary frameworks |
   |-------|---------|-------------------|
   | L4 Outcomes | Why — portfolio alignment | OKRs, Shape Up, Lean metrics |
   | L3 Governance | What — rules and intent | Constitution, FR/NFR, ADRs, BMAD PRD |
   | L2 Delivery | How organized — WPs and cadence | Spec Kitty, GSD phases, Scrum (optional) |
   | L1 Execution | How done — code deltas | OpenSpec, Spec-Kit tasks, worktrees |
   | L0 Evidence | Proof — audit and links | trace.json, TraceLink, CI, worklogs |

2. **Runtime ownership:**

   | Layer | AgilePlus | Tracera (embedded) |
   |-------|-----------|-------------------|
   | L4 | Charter hooks (future) | Initiative ↔ requirement linking |
   | L3 | FSM, GovernanceContract, harmonizer | Contract read, FR ingest |
   | L2 | WP lanes, claim engine | CoverageMatrix build |
   | L1 | Worktrees, MCP, spec CLI | Artifact ingest, impact API |
   | L0 | trace-validator, audit chain | TraceLink store, RTM export |

3. **Framework selection by change type** follows FRAMEWORK_ANALYSIS §4.4 (bug → GSD quick;
   feature → Spec Kitty; brownfield → OpenSpec + Tracera impact; epic → BMAD; portfolio →
   OKRs + Shape Up).
4. **SAFe / Waterfall / PMBOK / PRINCE2** vocabulary is permitted at **L4 and compliance
   export only** — not as execution FSMs. Six Sigma tollgate *concept* maps to L0 CI gates.
5. **No new layer may bypass L0** on merge. L4 approval does not waive trace-validator.

## Consequences

- Documentation and agent skills reference L0–L4 consistently.
- Tooling roadmap prioritizes layer gaps (e.g. L4 charter CLI) over new frameworks.
- Enterprise customers get PMBOK/PRINCE2 labels on the same spine — not parallel processes.
- Framework churn is absorbed by harmonizer + layer mapping, not new roots.

## References

- [`FRAMEWORK_ANALYSIS.md`](../harmonization/FRAMEWORK_ANALYSIS.md) §4.2–§4.4
- [`UNIFIED_PM_MODEL.md`](../harmonization/UNIFIED_PM_MODEL.md) §4, §7–§8
- ADR-0011, ADR-0012, ADR-0013
