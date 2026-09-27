# phenotype-hub (absorbed)

| Field | Value |
|-------|-------|
| **Source repo** | https://github.com/KooshaPari/phenotype-hub |
| **Absorption date** | 2026-06-18 |
| **Registry wave** | G19 (wave15 stub absorption) |
| **Disposition** | ABSORB |
| **Canonical owner** | **phenotype-infra** (this repo) |

## Summary

`phenotype-hub` was an archived governance scaffold — agent instructions, functional-requirements tracker, journey traceability docs, and worklogs — with no runtime implementation. Per registry wave G19, its documentation role is absorbed here. The archived repo remains read-only for history; new edits belong in `phenotype-infra`.

## Absorbed document index

| Source path (phenotype-hub) | Role | Canonical surface in phenotype-infra |
|-----------------------------|------|-------------------------------------|
| `README.md` | Hub overview and layout | This file + [ABSORPTION_INDEX.md](../../ABSORPTION_INDEX.md) |
| `AGENTS.md` | Agent governance contract | [docs/governance/](../../governance/) policies and runbooks |
| `CLAUDE.md` | Claude/Codex workflow notes | Repo root `AGENTS.md` / `CLAUDE.md` (when present) |
| `CONTRIBUTING.md` | Contribution guide | Root [CONTRIBUTING.md](../../../CONTRIBUTING.md) |
| `FUNCTIONAL_REQUIREMENTS.md` | FR traceability stub | [docs/specs/](../../specs/) and journey manifests |
| `SECURITY.md` | Security reporting | Root [SECURITY.md](../../../SECURITY.md) |
| `docs/worklogs/README.md` | Work audit index | [docs/sessions/](../../sessions/) session worklogs |
| `docs/worklogs/worklog.md` | Work audit entries | [docs/sessions/](../../sessions/) |
| `docs/operations/journey-traceability.md` | Journey evidence standard | [docs/operations/journey-traceability.md](../../operations/journey-traceability.md) |
| `docs/operations/iconography/SPEC.md` | Iconography spec | [docs/operations/iconography/SPEC.md](../../operations/iconography/SPEC.md) |
| `docs/journeys/manifests/README.md` | Journey manifest index | [docs/journeys/manifests/README.md](../../journeys/manifests/README.md) |
| `.github/` | GitHub workflows and templates | [`.github/`](../../../.github/) in this repo |

## Registry reference

- `phenotype-registry` project stub: `projects/phenotype-hub.json` (`disposition: ABSORB`, `absorb_target: phenotype-infra`)
- ECOSYSTEM_MAP P8: merge hub scaffold into infra; registry keeps redirect only

## Do not

- Open new feature work against the archived `phenotype-hub` repo.
- Treat `phenotype-hub` as a runtime or routing SSOT — use `phenotype-infra` ADRs, specs, and runbooks instead.
