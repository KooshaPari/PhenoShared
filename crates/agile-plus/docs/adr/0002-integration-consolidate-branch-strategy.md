# ADR-0002: Integration/Consolidate Branch Strategy

## Status
Accepted

## Context
AgilePlus has accumulated multiple feature branches (30+) that need to be unified before
merging to main. A single integration branch avoids merge-conflict accumulation and allows
CI to validate the combined state.

## Decision
All feature branches are consolidated onto `integration/consolidate` via FF-merge (--ff-only,
fallback --no-ff). Anti-wipe gate (git diff --name-status, reject if deletions > 0) is applied
before every merge. A single PR from integration/consolidate → main is created once CI is green.

## Consequences
- CI runs on the unified branch surface rather than per-feature
- Merge conflicts are resolved once, in integration/consolidate
- Main remains protected; no direct pushes
- Spec eco-029 tracks this consolidation work
