# Journey Traceability

Implements the phenotype-infra journey-traceability standard for AgilePlus as the spec-driven project management system of record.

## Traceability Model

Every user-facing or agent-facing flow should be traceable across:

1. **FR/NFR** — requirement ID and user story from `docs/requirements/agileplus-frnfr.md`.
2. **Spec** — acceptance criteria, invariant, and non-regression constraint.
3. **Docs** — operator/user documentation and rich media placeholders.
4. **Code** — domain crate, application use case, adapter, API, CLI, dashboard, or sync surface implementing the flow.
5. **Tests/Gates** — unit, integration, BDD, lint, coverage, and journey verification acting as autograders.
6. **Evidence** — journey manifest, recording/keyframes, and evaluation verdict.

## User-Facing and Agent-Facing Flows

| Flow | Requirement | Implementation surface | Autograder gates | Evidence status |
| --- | --- | --- | --- | --- |
| Create and validate a rich project backlog | FR-AGP-001, NFR-AGP-005 | `agileplus-domain`, `agileplus-application`, CLI/API project commands | domain invariant tests, use-case tests, BDD journey, eval verdict | Stubbed |
| Import a manifest into AgilePlus entities | FR-AGP-012, NFR-AGP-005 | `agileplus-import`, manifest parser, `ImportReport` | fixture import tests, error-report assertions, journey manifest | Stubbed |
| Sync GitHub issues/PRs into domain objects | FR-AGP-006, NFR-AGP-002 | `agileplus-github`, sync mapping, octocrab adapter | adapter contract tests, mocked GitHub fixtures, sync smoke | Stubbed |
| Persist and query synced project state | FR-AGP-003, FR-AGP-013, NFR-AGP-005 | `agileplus-sqlite`, repository ports, application use cases | repository tests, migration checks, query smoke, BDD journey | Stubbed |
| Dashboard shows traceable epics/stories | FR-AGP-014, NFR-AGP-006 | dashboard endpoint, React/Askama UI, seed database | UI smoke, JSON endpoint tests, screenshot journey, accessibility check | Stubbed |
| Agent triage maps work to intent and priority | FR-AGP-017, NFR-AGP-005 | triage engine, `Intent::Docs`, default priority mapping | rule tests, fixture payloads, eval verdict | Stubbed |

## Rich Media Stubs

<!-- RICH-MEDIA-STUB type="animated-gif" subject="Project backlog creation and invariant validation" journey="create-project-backlog" status="TODO" -->
> **Stub (TODO):** AgilePlus project backlog creation — project, epic, feature, story, invariant validation, and saved state. *Capture pending; the linked asset `../assets/rich-media/agileplus/create-project-backlog.gif` is intentionally absent and will be recorded when the journey manifest is captured.*

*Expected capture: create a project backlog through the CLI/API/UI path, show invalid-state rejection, then show the valid backlog persisted and queryable.*

<!-- RICH-MEDIA-STUB type="annotated-screenshot" subject="Manifest import report" journey="manifest-import-report" status="TODO" -->
> **Stub (TODO):** AgilePlus manifest import report — imported entities, skipped rows, validation errors, and traceability IDs. *Capture pending; the linked asset `../assets/rich-media/agileplus/manifest-import-report.png` is intentionally absent and will be recorded when the journey manifest is captured.*

*Expected capture: import a deterministic fixture manifest, annotate success/failure counts, and link imported entities back to FR-AGP-012.*

<!-- RICH-MEDIA-STUB type="journey-eval" subject="GitHub sync evidence verdict" journey="github-sync-evidence" status="TODO" -->
> **Stub (TODO):** AgilePlus GitHub sync evidence — fixture issue, mapped story, sync provenance, and eval verdict. *Capture pending; the linked asset `../assets/rich-media/agileplus/github-sync-evidence.png` is intentionally absent and will be recorded when the journey manifest is captured.*

*Expected capture: sync GitHub fixture data, prove mapped domain entities match expected state, and attach a pass/fail eval verdict for FR-AGP-006 and NFR-AGP-002.*

<!-- RICH-MEDIA-STUB type="annotated-screenshot" subject="Dashboard traceable epics and stories" journey="dashboard-traceable-work" status="TODO" -->
> **Stub (TODO):** AgilePlus dashboard — epics, stories, FR/NFR links, and backlog status rollup. *Capture pending; the linked asset `../assets/rich-media/agileplus/dashboard-traceable-work.png` is intentionally absent and will be recorded when the journey manifest is captured.*

*Expected capture: open the seeded dashboard, show epics/stories with FR/NFR IDs, and verify the JSON endpoint agrees with the rendered UI.*

<!-- RICH-MEDIA-STUB type="journey-eval" subject="Agent triage intent and priority verdict" journey="agent-triage-intent-priority" status="TODO" -->
> **Stub (TODO):** AgilePlus triage verdict — raw work item, inferred intent, priority, and rule trace. *Capture pending; the linked asset `../assets/rich-media/agileplus/agent-triage-intent-priority.png` is intentionally absent and will be recorded when the journey manifest is captured.*

*Expected capture: run the triage engine against fixture work items, show inferred intent/priority, and attach an eval verdict checking expected classifications.*

## Journey Manifests

Journey manifests should live in `docs/journeys/manifests/` and include:

- FR/NFR IDs covered by the journey;
- CLI command, API route, dashboard route, or agent entrypoint used to reproduce the flow;
- fixture data required for deterministic replay;
- expected screenshots/GIFs/keyframes;
- tests and gates that must pass before the journey is accepted;
- eval verdict schema and pass/fail criteria.

## Autograder Gates

Minimum gates before marking a journey complete:

- `cargo test --workspace` for domain/application behavior;
- targeted crate tests for imports, sync, persistence, and triage;
- dashboard/API smoke for user-visible flows;
- BDD journey replay for FR/NFR user stories;
- doc link validation for every referenced rich media asset;
- journey manifest validation via `phenotype-journey verify` when available;
- eval verdict linked to the FR/NFR IDs in the manifest.

## Status

- [x] Identify initial FR/NFR-backed flows from `docs/requirements/agileplus-frnfr.md`
- [x] Stub rich media embeds for expected screenshots/GIFs/evals
- [ ] Author manifests in `docs/journeys/manifests/`
- [ ] Record journey captures for each flow
- [ ] Run `phenotype-journey verify` in CI
