# Requirements traceability

**Status:** adopted · **Applies to:** all tracked work.

## Convention

Every piece of work traces to a requirement and a plan item:

- A **FR/NFR requirement ID in Tracera**, wired as a chain: **requirement → code → test → PR** (TraceLinks).
- An **AgilePlus Epic/Story** the work rolls up to.
- The two are linked, so a requirement, its implementing commits, its tests, and its merged PR are all reachable from one ID.

Cite a **requirement ID per task**. Work that ships without a traceable requirement should be backfilled with one.

## Why

Traceability answers "why does this code exist and is it tested?" for every line, and lets us prove coverage of functional/non-functional requirements rather than asserting it. It also makes scope changes visible — a requirement with no code, or code with no requirement, both show up.

## Do / Don't

- **DO** open work against an existing FR/NFR, or create the requirement first if none fits.
- **DO** reference the requirement ID in the PR body so the TraceLink closes.
- **DON'T** merge feature work with no requirement and no story.
