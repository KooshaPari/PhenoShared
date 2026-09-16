# Journey Traceability

Journey traceability is the practice of documenting important product or
operator flows with both narrative and evidence.

## Why It Matters

Patterns are easier to trust when they come with proof:

- keyframes that show the important states
- recordings that show the full interaction
- stable names so the evidence can be reused in reviews and audits

This mirrors the shared Phenotype standard documented in:

- [phenotype-infra journey standard](https://github.com/kooshapari/phenotype-infra/blob/main/docs/governance/journey-traceability-standard.md)
- hwLedger, which is the reference implementation for `ShotGallery` and
  `RecordingEmbed`

## Minimum Contract

When a handbook entry describes a real flow, it should include:

1. A short explanation of the flow.
2. The important states or steps.
3. A reference to the journey evidence bundle.
4. A link back to the repo or spec that produced the journey.

## Recommended Structure

For repos that support it directly:

- `ShotGallery` for keyframes
- `RecordingEmbed` for replayable recordings
- stable tape ids
- keyframe paths that are stable over time

For repos without a docs-site embed surface, document the same evidence contract
in plain Markdown and link to the artifacts.

## Adoption Notes

- `phenodocs` carries the hub-level governance page.
- `PhenoProject` should use the same pattern for workspace-level flows.
- Product repos should follow the same contract where user journeys are visible.
