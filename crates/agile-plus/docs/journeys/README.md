# Journeys

User-facing and agent-facing flows for AgilePlus, modelled on the
hwLedger `add-rich-journey-embeds-to-docs-v10` exemplar
(`docs/journeys/manifests/README.md` + per-flow pages with rich-media
stubs). Every flow documented here MUST be traceable across **spec →
docs → tests → code → stub → eval**; a missing link at any layer fails
the docs lint (eco-021, eco-022, eco-024).

## Canonical Layout

```
docs/
  journeys/
    README.md                              # this file
    <journey-id>.md                        # one per documented flow
    manifests/
      <journey-id>.journey.yaml            # rich-media manifest (eval contract)
    assets/
      stubs/                               # stub placeholders for capture-in-flight media
        <journey-id>/                      # one dir per journey
          frame-###.gif|png                # stub placeholders
  templates/
    journey-template.md                    # page template (this dir's contract)
    bdd-feature-template.feature           # BDD template linked from the page template
```

A journey page is **always** anchored to an FR/NFR row in
[`FUNCTIONAL_REQUIREMENTS.md`](../../FUNCTIONAL_REQUIREMENTS.md) and to
a `kitty-spec` slug under [`kitty-specs/`](../../kitty-specs/). The
journey page is a thin human-readable narrative; the executable
contract is the `<journey-id>.journey.yaml` manifest (eval) and the
`<journey-id>.feature` BDD file (acceptance). Rich-media evidence
(keyframes, recordings) lives under
`docs/journeys/assets/stubs/<journey-id>/` as git-tracked placeholders
until `phenotype-journey capture` produces real artifacts.

## Template

Every journey page MUST follow the canonical template at
[`../templates/journey-template.md`](../templates/journey-template.md).
The template enforces, in order:

1. **YAML front-matter** with `fr_id`, `spec_slug`, `spec_anchor`,
   `status`, `captured_at`. This header is the contract that
   `tooling/trace-validator/` (eco-024) and the eco-021 autograder
   consume; the validator refuses a journey whose `fr_id` is not
   registered in `FUNCTIONAL_REQUIREMENTS.md`.
2. **User story** paragraph, one block, written in the
   "As a `<role>`, I want `<capability>`, so that `<outcome>`" voice.
3. **Acceptance criteria** as an ordered list, each item addressable
   from the BDD scenarios in the companion `.feature` file.
4. **Steps** with one stub media reference per transition. Stubs use
   the Phenotype-org `<!-- RICH-MEDIA-STUB ... --> ... <!-- END-RICH-MEDIA-STUB -->`
   comment pair (see [`../../RICH_MEDIA.md`](../../RICH_MEDIA.md)). Each
   stub points at a file under
   `docs/journeys/assets/stubs/<journey-id>/` and is greppable by
   `journey="<journey-id>"`.
5. **Traceability table** with explicit columns `AC | Criterion |
   Test / Evidence`. The `Test / Evidence` cell must point at a real
   path (test file, BDD scenario, or YAML manifest) — never at
   `TBD`.
6. **Eval checklist** enumerating the autograder gates that must pass
   before the journey can be marked `status: captured` or
   `status: published`.

## Stub Convention

Until a real capture is recorded, every transition in the **Steps**
section carries a stub block:

```html
<!-- RICH-MEDIA-STUB type="recording-gif" subject="<what the media will show>" journey="<journey-id>" status="TODO" -->
> **[RICH MEDIA PLACEHOLDER]** *<one-line human description of what will go here>*
<!-- END-RICH-MEDIA-STUB -->
```

Rules (strict, enforced by `phenotype-journey lint` once wired into
eco-021):

- `journey` attribute MUST equal the page's `<journey-id>` and match a
  manifest under `docs/journeys/manifests/`.
- `type` MUST be one of `annotated-screenshot | recording-mp4 | recording-gif`
  (Phenotype-org canonical set; see
  [`../../RICH_MEDIA.md`](../../RICH_MEDIA.md)).
- The image path referenced in the stub (when present) MUST live under
  `docs/journeys/assets/stubs/<journey-id>/`.
- The stub MUST wrap a single line of human-readable description so
  fill-agents can replace it without diffing the comment fences.
- `status` MUST be one of `TODO` (un-captured) | `CAPTURED` (raw asset
  exists) | `PUBLISHED` (asset is embedded in the live docs site).

A `.gitkeep` placeholder lives at
[`assets/stubs/.gitkeep`](./assets/stubs/.gitkeep) so the stub tree
exists in fresh checkouts. Per-journey stub directories are created
on demand when the first stub for a journey is authored.

## Manifest Convention

The companion manifest
`docs/journeys/manifests/<journey-id>.journey.yaml` is the **eval
contract** for the journey. It mirrors
`phenotype_journey_core::Manifest` (hwLedger exemplar) and lists one
`steps[]` entry per Acceptance Criterion with `must_contain`,
`must_contain_regex`, `must_not_contain`, and `expected_exit`
assertions. The manifest is the only artifact `phenotype-journey
verify` reads; missing manifests fail the eco-021 docs gate.

```yaml
id: <journey-id>
intent: <one-line user story>
keyframe_count: <int>
passed: false                       # set true after `phenotype-journey verify` accepts
recording: assets/stubs/<journey-id>/replay.gif
steps:
  - index: 1
    slug: <short-state-name>
    assertions:
      must_contain: ["..."]
      must_not_contain: ["error:"]
      expected_exit: 0
      ocr_required: true
```

## Spec Linkage

Every journey page MUST cross-link three layers:

| Layer | Where it lives | Required link from the page |
|-------|----------------|-----------------------------|
| FR/NFR | [`FUNCTIONAL_REQUIREMENTS.md`](../../FUNCTIONAL_REQUIREMENTS.md) | `fr_id` in front-matter; row in Traceability table |
| Spec | [`kitty-specs/<spec_slug>/spec.md`](../../kitty-specs/) | `spec_slug` + `spec_anchor` in front-matter; "User story" mirrors the spec verbatim |
| BDD | `specs/<spec_slug>/bdd/<journey-id>.feature` (or a sibling path) | one `Scenario:` per AC; linked from Traceability table |

Spec linkage is verified by `tooling/trace-validator/` (eco-024) on
every PR. A journey page that points at a missing slug, a missing
anchor, or an unregistered FR ID fails the gate.

## BDD Template

BDD files for journeys MUST be authored against
[`../templates/bdd-feature-template.feature`](../templates/bdd-feature-template.feature).
The template uses the canonical Gherkin shape: one `Feature:`, one
`Background:`, one `Scenario:` per AC, and `@fr-XXX` tags on every
scenario so eco-024 can map scenarios back to FR rows. Scenario names
are stable — renaming a scenario is a breaking change to the BDD
contract and requires a Traceability table update on the journey
page.

## Adoption Checklist

When adding a new journey:

- [ ] Register the FR row in
      [`FUNCTIONAL_REQUIREMENTS.md`](../../FUNCTIONAL_REQUIREMENTS.md)
      with `status: proposed` and a stub trace.
- [ ] Copy [`../templates/journey-template.md`](../templates/journey-template.md)
      to `docs/journeys/<journey-id>.md` and fill the front-matter.
- [ ] Copy
      [`../templates/bdd-feature-template.feature`](../templates/bdd-feature-template.feature)
      to `specs/<spec_slug>/bdd/<journey-id>.feature` and author one
      `Scenario:` per AC.
- [ ] Author `docs/journeys/manifests/<journey-id>.journey.yaml` with
      at least one `must_not_contain: ["error:"]` step and a final
      `expected_exit: 0` step.
- [ ] Add a stub block to every transition in **Steps**; create
      `docs/journeys/assets/stubs/<journey-id>/` if needed.
- [ ] Cross-link the journey page from the kitty-spec user-story
      section.
- [ ] Run `cargo run -p tooling-trace-validator -- --strict` and
      confirm green.

## Status

- [x] Identify initial FR/NFR-backed flows from
      `docs/requirements/agileplus-frnfr.md`
- [x] Author canonical journey page template
- [x] Author canonical BDD feature template
- [ ] Author manifests in `docs/journeys/manifests/`
- [ ] Wire `phenotype-journey lint` into the eco-021 autograder
- [ ] Run `phenotype-journey verify` in CI

## See also

- [`../../RICH_MEDIA.md`](../../RICH_MEDIA.md) — Phenotype-org
  rich-media stub convention (authoritative).
- [`../operations/journey-traceability.md`](../operations/journey-traceability.md) —
  AgilePlus journey-traceability standard.
- [`../../FUNCTIONAL_REQUIREMENTS.md`](../../FUNCTIONAL_REQUIREMENTS.md) —
  canonical FR registry.
- [`../../kitty-specs/eco-022-rich-journey-embeds/spec.md`](../../kitty-specs/eco-022-rich-journey-embeds/spec.md) —
  source spec for this directory's contract.
- hwLedger exemplar:
  `<REDACTED>/hwLedger@codex/add-rich-journey-embeds-to-docs-v10` →
  `docs/journeys/manifests/README.md`.
