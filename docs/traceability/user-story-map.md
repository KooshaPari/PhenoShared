# User Story -> Journey -> FR Traceability Map

- **Repo:** PhenoProject
- **Authoritative FR doc:** [`FUNCTIONAL_REQUIREMENTS.md`](../../FUNCTIONAL_REQUIREMENTS.md)
- **Journey standard:** [`docs/operations/journey-traceability.md`](../operations/journey-traceability.md)
- **Status date:** 2026-06-05
- **Note:** All seven FRs are stubs (`Status: Stub`, `Test Status: Not yet written`). Source / test / journey columns are populated where the existing code/test layout already maps to the intent, and `[ ]` boxes mark which rows still need a journey manifest, code, test, and gate wired up. The FR-005 / FR-006 / FR-007 rows are the lowest-coverage rows because they have no test or journey artifact yet.

## Legend

- **Code:** Source path(s) that implement the story today.
- **Tests:** Test path(s) that exercise the code (or `none` if only a smoke import exists).
- **Journey:** Path to a journey manifest/evidence bundle, or `none` if not yet produced.
- **Gate:** The CI workflow that should enforce the row (or `none` if missing).
- **Checkboxes** track the four artifacts the row needs: journey manifest, code, test, gate.

## Traceability Table

| # | User story | FR id | Source file(s) | Test file(s) | Journey page (planned/produced) | Gate | Manifest | Code | Test | Gate wired |
|---|------------|-------|----------------|--------------|---------------------------------|------|----------|------|------|------------|
| 1 | As a project lead, I can create and manage a Planify project workspace end-to-end | FR-001 Project workflow management | `rust/Planify/apps/api/plane/app/views/workspace/base.py`, `rust/Planify/apps/api/plane/app/views/project/base.py`, `rust/Planify/apps/web/app/routes/core.ts` | `rust/Planify/apps/api/plane/tests/contract/app/test_workspace_app.py`, `rust/Planify/apps/api/plane/tests/contract/app/test_project_app.py`, `tests/smoke_test.go` (FR-001 trace) | `docs/journeys/manifests/planify-workspace-create.json` (planned) | `.github/workflows/fr-coverage.yml` | [ ] | [x] | [x] | [ ] |
| 2 | As a team member, I can schedule and execute cycles and tasks inside a project | FR-002 Task scheduling and execution | `rust/Planify/apps/api/plane/app/views/cycle/`, `rust/Planify/apps/api/plane/bgtasks/issue_automation_task.py`, `rust/Planify/apps/api/plane/bgtasks/email_notification_task.py` | `rust/Planify/apps/api/plane/tests/contract/api/test_cycles.py` | `docs/journeys/manifests/planify-cycle-run.json` (planned) | `.github/workflows/quality-gate.yml` | [ ] | [x] | [x] | [ ] |
| 3 | As a multi-stack maintainer, I can run Planify (TS/Bun) and KaskMan (Go/Node) side by side | FR-003 Multi-language project support | `rust/Planify/` (TS monorepo, Turbo + pnpm), `go/KaskMan/` (Node CLI + Go-style services) | `rust/Planify/packages/codemods/tests/remove-directives.spec.ts`, `rust/Planify/packages/codemods/tests/function-declaration.spec.ts`, `go/KaskMan/src/rnd-module/RnDModule.test.js` | `docs/journeys/manifests/multistack-bootstrap.json` (planned) | `.github/workflows/ci.yml` | [ ] | [x] | [x] | [x] |
| 4 | As a build engineer, I can resolve and track dependencies across Planify packages | FR-004 Dependency resolution and tracking | `rust/Planify/pnpm-workspace.yaml`, `rust/Planify/turbo.json`, `rust/Planify/package.json` (catalog deps), `rust/Planify/apps/api/plane/requirements.txt` | `rust/Planify/apps/live/tests/services/pdf-export/effect-utils.test.ts`, `rust/Planify/apps/live/tests/lib/pdf/pdf-rendering.test.ts` | `docs/journeys/manifests/planify-dep-graph.json` (planned) | `.github/workflows/ci.yml` | [ ] | [x] | [x] | [x] |
| 5 | As a release engineer, I can generate and publish build artifacts | FR-005 Artifact generation and publishing | `rust/Planify/apps/api/Dockerfile.api`, `rust/Planify/apps/web/Dockerfile.web`, `rust/Planify/apps/space/Dockerfile.space`, `rust/Planify/deployments/` | none | none | none | [ ] | [x] | [ ] | [ ] |
| 6 | As an operator, I can manage configuration across environments (env, secrets, Doppler) | FR-006 Configuration management | `rust/Planify/.env.example`, `rust/Planify/doppler.yaml`, `rust/Planify/apps/api/plane/settings/`, `go/KaskMan/.env.example`, `go/KaskMan/dashboard-memory.json` | `rust/Planify/apps/api/plane/tests/contract/app/test_authentication.py` (instance setup touches settings) | none | none | [ ] | [x] | [x] | [ ] |
| 7 | As an integrator, I can plug into external services via webhooks, exporters, and license checks | FR-007 Integration with external services | `rust/Planify/apps/api/plane/app/views/webhook/`, `rust/Planify/apps/api/plane/bgtasks/export_task.py`, `rust/Planify/apps/api/plane/license/`, `go/KaskMan/src/interfaces/api/server.js` | `rust/Planify/apps/api/plane/tests/contract/app/test_api_token.py` | none | none | [ ] | [x] | [x] | [ ] |

## Coverage Summary

| FR id | Code present | Test present | Journey manifest | Gate wired | Coverage |
|-------|--------------|--------------|------------------|------------|----------|
| FR-001 | yes | yes (contract + smoke) | planned | partial | medium |
| FR-002 | yes | yes (cycle contract) | planned | partial | medium |
| FR-003 | yes | yes (codemods + KaskMan) | planned | yes | high |
| FR-004 | yes | yes (live/pdf unit) | planned | yes | high |
| FR-005 | yes | no | no | no | low |
| FR-006 | yes | partial (auth touches settings only) | no | no | low |
| FR-007 | yes | yes (api token only) | no | no | low |

## Lowest-Coverage Stories (Top 3)

1. **FR-005 Artifact generation and publishing** - no test, no journey manifest, no dedicated gate. Only Dockerfiles and a `deployments/` directory exist.
2. **FR-006 Configuration management** - only one contract test (auth/instance setup) tangentially covers settings; no journey and no dedicated gate. Surface spans `.env`, Doppler config, and Django settings.
3. **FR-007 Integration with external services** - only the API token contract test exists; webhook, exporter, and license flows have no dedicated tests, no journey evidence, and no gate.

## Next Actions

- [ ] Flesh out FR-001..FR-007 descriptions in `FUNCTIONAL_REQUIREMENTS.md` (currently empty stubs).
- [ ] Add a journey manifest JSON for each of the seven stories under `docs/journeys/manifests/`.
- [ ] Add Playwright e2e coverage for at least one story per gate (FR-005/006/007 are the biggest gaps).
- [ ] Wire `.github/workflows/fr-coverage.yml` to a real FR/test parser (currently a no-op echo step).
