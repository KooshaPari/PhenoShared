# ADR-0015: Process Machine Over Checklist Governance

## Status

Proposed

## Context

Before embed re-architecture, Tracera evaluated governance and progression predicates as a
**checklist**: coverage cells present, links exist, predicates pass — without owning
`FeatureState` transitions or binding `GovernanceContract` versions to features.

AgilePlus implements a **process machine**:

- Versioned `GovernanceContract` bound at feature creation (ADR-0007).
- `FeatureState` FSM rejects illegal transitions.
- `ProgressionGate` + `GateContext` evaluate claims before layer advancement (ADR-0009).
- Resource `ClaimStore` coordinates exclusive WP execution.

Checklist governance allows teams to "look green" in Tracera while the FSM sits in an
inconsistent state, or to merge PRs without AgilePlus ship gates when Tracera is bypassed.

## Decision

1. **Governance is enforced by the process machine, not by graph color.** Tracera
   supplies evidence inputs; AgilePlus FSM + claim engine makes allow/deny decisions.
2. **Checklist predicates remain** as **inputs** to `GateContext` — they are not standalone
   pass/fail surfaces. A green CoverageMatrix is necessary but not sufficient for transition.
3. **Contract binding is mandatory** before feature leaves `Draft`. Unbound features cannot
   reach `Specified`.
4. **Tracera UI displays machine state:** dashboard shows FSM state + predicate breakdown +
   contract version — never an independent "compliance score" that contradicts FSM.
5. **Post-embed:** Tracera MUST call AgilePlus `EvaluateGovernance` / progression APIs;
   local re-implementation of `ProgressionGate` in Go is removed over migration (ADR-0017).

## Consequences

- Tracera becomes a faithful projection of process truth, not a parallel governance system.
- Predicate additions require spine + AgilePlus release, not Tracera-only deploy.
- Agents receive one denial message stream from AgilePlus; Tracera renders it.
- Compliance teams gain RTM export **backed by enforced transitions**, not link lint.

## References

- ADR-0007, ADR-0009, ADR-0010
- ADR-0011: Tracera embeds AgilePlus
- [`UNIFIED_PM_MODEL.md`](../harmonization/UNIFIED_PM_MODEL.md) §2 P1, §5
- [`FRAMEWORK_ANALYSIS.md`](../harmonization/FRAMEWORK_ANALYSIS.md) — AgilePlus machine-verifiable FR trace
