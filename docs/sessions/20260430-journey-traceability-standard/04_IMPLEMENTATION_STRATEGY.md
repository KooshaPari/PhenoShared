# Implementation Strategy

## Approach

Start with one canonical governance doc in `phenotype-infra` and make the
shared local parity page point at it. That gives the ecosystem one source of
truth for docs evidence.

## Why This Shape

- Keeps the standard visible where the other shared infra lives.
- Lets repo-specific docs adopt the same contract without re-explaining it.
- Avoids inventing a second or third tracing pattern.

## Follow-On Work

- Update repo docs indices to reference the standard.
- Add journey pages to the highest-value repos first.
- Backfill recordings and keyframes for flows that already have screenshots.

## Notes

The goal is not just "more screenshots." The goal is a traceable journey bundle
that can be used in reviews, audits, and handoffs.
