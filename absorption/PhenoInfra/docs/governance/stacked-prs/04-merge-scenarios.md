# Merge Scenarios

## Tree example

A: playback core (alpha)
  ├─ B: cache layer (beta)
  └─ C: advanced renderer (beta/rc)

C is in the same feature family only if C depends on A (directly or transitively).
If C is renderer risk, it must stay at beta/rc even if A is on main.

## Rule of merge order

- Never merge a child PR before its required parent PR.
- Do not merge PR-3 with API contracts from PR-2 unless PR-2 is merged.
- Prefer small PR slices, each passing its own gates.

## Practical check before merge

- All depends_on IDs resolved
- Rollback plan is real and tested
- Channel label aligns with risk and migration strategy
