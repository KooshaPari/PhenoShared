<!--
Template: journey page
Owner: docs/journeys/README.md (mirrors hwLedger add-rich-journey-embeds-to-docs-v10)
Linked spec: kitty-specs/eco-022-rich-journey-embeds/spec.md
Linked FR: <fr_id> (row in FUNCTIONAL_REQUIREMENTS.md)
Linked BDD: specs/<spec_slug>/bdd/<journey-id>.feature

Copy this file to `docs/journeys/<journey-id>.md`, fill the placeholders
in angle brackets, and delete the leading `<!--` block. The contract
enforced by tooling/trace-validator (eco-024) and the eco-021
autograder is:

  1. Front-matter is mandatory and well-formed.
  2. `fr_id` is registered in FUNCTIONAL_REQUIREMENTS.md.
  3. `spec_slug` + `spec_anchor` resolve to a real file + heading.
  4. The Traceability table maps every AC to a real test/evidence path.
  5. The Eval checklist enumerates the autograder gates that must
     pass before `status` may move from `pending-capture` to
     `captured` or `published`.
-->
---
fr_id: <FR-XXX-NNN>                # registered in FUNCTIONAL_REQUIREMENTS.md
spec_slug: <kitty-spec-slug>        # e.g. eco-022-rich-journey-embeds
spec_anchor: "#<heading-anchor>"    # exact heading anchor in the spec
status: pending-capture             # pending-capture | captured | published | deprecated
captured_at: null                   # ISO 8601 timestamp once status flips
---

# Journey: <Human-Readable Title>

> **Status: `<status>`** — `<fr_id>`. See
> `kitty-specs/<spec_slug>/spec.md` (anchor `spec_anchor`) for the
> source of truth and
> `specs/<spec_slug>/bdd/<journey-id>.feature` for the executable
> acceptance scenarios. The rich-media manifest lives at
> [`docs/journeys/manifests/<journey-id>.journey.yaml`](../journeys/manifests/<journey-id>.journey.yaml).

## User story

As a **<role>**, I want <capability>, so that <outcome>. This block
MUST mirror the spec's user story verbatim. If the spec and the
journey page disagree, the spec wins and the journey is treated as
out-of-date by the trace validator.

## Acceptance criteria

1. **AC1** — <one-sentence criterion, addressable from a BDD Scenario>.
2. **AC2** — <one-sentence criterion>.
3. **AC3** — <one-sentence criterion>.

(Add or remove ACs to match the FR. Each AC MUST be reachable from a
BDD scenario in the linked `.feature` file and from a row in the
Traceability table below.)

## Steps

1. <First transition — e.g. "Run `agileplus <subcommand>`">
   <!-- RICH-MEDIA-STUB type="recording-gif" subject="<short description of what the GIF will show>" journey="<journey-id>" status="TODO" -->
   > **[RICH MEDIA PLACEHOLDER]** *<one-line human description of what will go here>*
   <!-- END-RICH-MEDIA-STUB -->
2. <Second transition — e.g. "Open `http://localhost:<port>/health`">
   <!-- RICH-MEDIA-STUB type="annotated-screenshot" subject="<short description>" journey="<journey-id>" status="TODO" -->
   > **[RICH MEDIA PLACEHOLDER]** *<one-line human description of what will go here>*
   <!-- END-RICH-MEDIA-STUB -->
3. <Third transition — e.g. "Confirm `healthy: true` and numeric latency">
   <!-- RICH-MEDIA-STUB type="recording-gif" subject="<short description>" journey="<journey-id>" status="TODO" -->
   > **[RICH MEDIA PLACEHOLDER]** *<one-line human description of what will go here>*
   <!-- END-RICH-MEDIA-STUB -->
4. <Fourth transition — e.g. "Hit the JSON endpoint and compare payload">
   <!-- RICH-MEDIA-STUB type="annotated-screenshot" subject="<short description>" journey="<journey-id>" status="TODO" -->
   > **[RICH MEDIA PLACEHOLDER]** *<one-line human description of what will go here>*
   <!-- END-RICH-MEDIA-STUB -->

## Traceability

| AC | Criterion | Test / Evidence |
|----|-----------|-----------------|
| AC1 | <criterion verbatim> | `crates/<crate>/tests/<file>.rs::<test_name>` |
| AC2 | <criterion verbatim> | `specs/<spec_slug>/bdd/<journey-id>.feature::<scenario_name>` |
| AC3 | <criterion verbatim> | `docs/journeys/manifests/<journey-id>.journey.yaml` |
| AC4 | <criterion verbatim> | (repeat per AC) |

> **Rule:** every `Test / Evidence` cell MUST point at a real path
> that exists in the working tree at PR time. `TBD`, `TBA`, or empty
> cells fail the eco-021 docs gate.

## Eval checklist

- [ ] `cargo test -p <crate>` (or workspace) exits 0.
- [ ] All ACs above have at least one passing test in the linked
      `*.rs` file or BDD scenario.
- [ ] BDD scenarios in
      `specs/<spec_slug>/bdd/<journey-id>.feature` are one-to-one
      with the ACs.
- [ ] `docs/journeys/manifests/<journey-id>.journey.yaml` passes
      `phenotype-journey verify` (every `must_contain` /
      `must_not_contain` / `expected_exit` assertion holds).
- [ ] All stub blocks in **Steps** have a non-empty human-readable
      description and a `journey` attribute equal to `<journey-id>`.
- [ ] No existing spec under `kitty-specs/` or
      `docs/requirements/agileplus-frnfr.md` is regressed.
- [ ] `tooling/trace-validator` reports green for `<fr_id>`.

## See also

- [`../journeys/README.md`](../journeys/README.md) — journeys index
  and stub convention.
- [`../../RICH_MEDIA.md`](../../RICH_MEDIA.md) — Phenotype-org
  rich-media stub markers.
- `kitty-specs/<spec_slug>/spec.md` — source spec.
- `docs/journeys/manifests/<journey-id>.journey.yaml` — eval
  contract.
