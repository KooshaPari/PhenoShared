# Rich Journey Embeds — Plan

## Objective
Codify a journey-capture stub pattern in docs and enforce it via eco-021 autograder linting, with trace evidence for spec → docs → tests → code → stub.

## Scope
- Adopt hwLedger exemplar stub pattern as canonical.
- Extend the spec-first template to include a journey-stub section.
- Add a docs lint that scans for stubs and integrates with eco-021 autograder.

## Implementation Steps
1. Adopt the hwLedger exemplar stub pattern (`![journey:<slug>](capture/<slug>.gif)` or `<!-- EMBED journey:<slug> capture/<slug>.gif -->`).
2. Update spec-first template to include a journey-stub section per FR-walked page.
3. Add lint to scan docs for stubs; surface misses in eco-021 autograder.
