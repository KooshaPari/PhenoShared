# Specifications

## Standard

The journey-traceability standard requires each important repo flow to ship
with:

- a narrative page
- at least one keyframe gallery
- at least one recording embed
- stable asset naming and a stable tape id
- traceability metadata for repo, owner, date, and related work item

## Acceptance Criteria

- A repo doc can point to a single page and show the flow visually.
- The evidence is stable enough to be re-embedded later.
- The capture is tied back to a work item or ADR.
- Missing evidence is documented as a blocker, not hidden.

## Non-Goals

- Rewriting every existing repo docs site in this change.
- Defining a new viewer implementation.
- Forcing a single storage backend if a repo already has a working equivalent.

## Risks

- Some repos may have docs without a docs-site renderer.
- Some existing flows may only have screenshots and not recordings yet.
- Some repos may need capture work before they can adopt the standard fully.
