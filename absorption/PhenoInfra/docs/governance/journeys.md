# Journey Traceability

The Phenotype docs stack treats a journey as a traceable evidence bundle, not
just a narrative paragraph.

## Standard

Every important user-facing or operator-facing flow should include:

- a short explanation of the flow
- keyframes showing the important states
- a recording or replay that shows the full interaction
- stable asset names and stable tape ids
- a link back to the repo, issue, ADR, or work package that produced it

## Reference Shape

Use the hwLedger pattern as the model:

- `ShotGallery` for keyframes
- `RecordingEmbed` for recordings
- `cli-journeys/keyframes/<journey>/frame-###.png` for frame assets

The full standard lives in
[phenotype-infra/docs/governance/journey-traceability-standard.md](https://github.com/kooshapari/phenotype-infra/blob/main/docs/governance/journey-traceability-standard.md).

## Adoption Order

1. `phenodocs` itself should carry the rule so other repos can discover it.
2. `PhenoHandbook` should show pattern examples and anti-patterns.
3. `PhenoProject` should document workspace-level flows and worklogs.
4. Product repos should add the same evidence bundle to their docs.

## Missing Evidence

If a repo does not yet have keyframes or a recording for a flow, call that out
explicitly and link the blocker. Do not leave the journey undocumented.
