# ADR-0013: Unified Lifecycle and Gate Stack

## Status

Proposed

## Context

Frameworks in [`FRAMEWORK_ANALYSIS.md`](../harmonization/FRAMEWORK_ANALYSIS.md) each define
different lifecycle stages (OpenSpec fluid OPSX, Spec-Kit linear gates, GSD phase loop,
Spec Kitty WP lanes, Scrum sprints, Shape Up cycles). AgilePlus has `FeatureState` FSM and
WP sub-states; Tracera has no lifecycle — only graph freshness.

Without a reconciled lifecycle, agents encounter conflicting "what stage are we in?" signals
across tools.

## Decision

1. **Eight-stage unified spine** (Charter → Specify → Plan → Decompose → Execute → Verify
   → Evidence → Archive) as defined in [`UNIFIED_PM_MODEL.md`](../harmonization/UNIFIED_PM_MODEL.md) §4.
2. **Canonical FSM:** AgilePlus `FeatureState` is the sole authority for feature-level
   stage. Mapping:

   | Unified stage | FeatureState (indicative) |
   |---------------|---------------------------|
   | Charter | `Draft` |
   | Specify | `Specified` |
   | Plan | `Planned` |
   | Decompose | `Ready` |
   | Execute | `InProgress` |
   | Verify | `InReview` |
   | Evidence | `Approved` |
   | Archive | `Done` / `Shipped` |

3. **WP sub-lifecycle** within Execute–Verify: Spec Kitty lanes
   (`planned` → `claimed` → `in_progress` → `for_review` → `done`).
4. **Five-layer gate stack** evaluated in order: Outcome → Governance → Progression →
   Resource → CI. Failure at any layer blocks transition (fail closed).
5. **Scale-adaptive skipping:** `GovernanceContract` may declare `quick_mode` policies
   that collapse stages for chore/bugfix classes (GSD quick mode, OpenSpec fluid apply) —
   but MUST still pass L0 CI and record evidence.
6. **Tracera observes, does not advance:** State-change events emit to Tracera for graph
   annotation; Tracera API MUST NOT expose feature transition mutations post-embed (ADR-0011).

## Consequences

- One dashboard row per feature maps to one FSM state.
- Scrum sprints and Shape Up cycles are **cadence overlays** on L2/L4 — not parallel FSMs.
- BMAD phase depth scales ceremony within stages, not replace them.
- BDD fixtures and CLI tests target unified stage names.

## References

- [`UNIFIED_PM_MODEL.md`](../harmonization/UNIFIED_PM_MODEL.md) §4–§5
- ADR-0011: Tracera embeds AgilePlus
- ADR-0007, ADR-0009: governance and claim engine
- [`FRAMEWORK_ANALYSIS.md`](../harmonization/FRAMEWORK_ANALYSIS.md) §4.1 spine, §4.4 selection guide
