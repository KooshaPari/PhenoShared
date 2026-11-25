# DEPRECATED — phenoResearchEngine

**Date:** 2026-06-20
**Author:** orch-v11-w2-gamma (L6 SOTA sweep, sub-task 4 — deprecate)
**Status:** DEPRECATED (formal closure of archival process)
**Prior state:** Archived (2026-03-25, per `ARCHIVED.md`)

---

## 1. Deprecation notice

This repository is **DEPRECATED** as of 2026-06-20.

- The package `phenotype-research-engine` (PyPI) **no longer receives updates**.
- The repository is **read-only**.
- No new issues, PRs, or feature requests will be accepted.
- The package metadata (`pyproject.toml` classifiers) is updated to mark
  `Development Status :: 7 - Inactive`.
- The GitHub repository will be archived (read-only) by the orchestrator
  (KooshaPari) once the deprecation PR is merged.

## 2. Why deprecated (rationale)

The `phenotype-research-engine` was the original research orchestration system
for Phenotype agents. Its responsibilities have been absorbed into the
`packages/phenotype-research/` successor module inside the monorepo. Continuing
to maintain a separate, parallel research engine:

- duplicates observability surface (Tracera)
- duplicates task-scheduling surface (Tasken)
- duplicates config-loading surface (`phenotype-config` → `Configra`)
- fragments the substrate (per ADR-023)

## 3. Migration

See `ARCHIVED.md` for the original migration guide (2026-03-25). The
migration target is `packages/phenotype-research/` in the monorepo at
`/path/to/phenotype/repos/`.

Key changes:

1. **Imports** — `from phenotype_research_engine import ...` → `from phenotype.research import ...`
2. **Config** — uses `Configra` (formerly `phenotype-config`); env-var names changed
3. **Tracing** — uses `pheno-tracing` OTLP spans (ADR-012, ADR-036B); old structlog-only logging is dropped
4. **Tasking** — uses `phenotype-bus` event-bus + `pheno-port-adapter` hexagonal ports (ADR-014, ADR-038) instead of the legacy DAG runner
5. **Tests** — BDD/behave tests moved to monorepo's `tests/` tree

## 4. Backwards compatibility

A thin compatibility shim is available at `packages/phenotype-research/compat/`
that re-exports the public API under the old import paths. The shim is
**time-boxed to 90 days from 2026-06-20** (expiry: **2026-09-18**).

After 2026-09-18, the shim is removed and downstream consumers MUST migrate
to the new imports.

## 5. Files changed in this deprecation (local)

| File | Change |
|---|---|
| `pyproject.toml` | `Development Status :: 3 - Alpha` → `7 - Inactive`; description, keywords, deprecation URL |
| `CHANGELOG.md` | `[Unreleased]` section now records deprecation entry |
| `README.md` | Header status banner changed from "Archived" to "DEPRECATED" |
| `SPEC.md` | Status: "Draft" → "Deprecated" |
| `AGENTS.md` | Added deprecation operating instructions |
| `DEPRECATED.md` | **NEW** — this file |
| `findings/2026-06-20-sd-sota-04-deprecation.md` | **NEW** — sub-task 4 audit trail |

## 6. Out of scope (orchestrator actions)

The following actions require **orchestrator (KooshaPari) approval**:

- Archiving the GitHub repository via `gh repo archive --yes`
- Publishing a final `0.1.1` PyPI release marked as deprecated
- Removing the package from the Phenotype fleet index

These are documented in `findings/2026-06-20-sd-sota-04-deprecation.md`
§ "Out-of-scope orchestrator actions" and are NOT performed by this sub-task.

## 7. Provenance

- Sub-task: `sd-sota-04` in `FLEET_DAG.db`
- Audit author: orch-v11-w2-gamma
- Plan reference: `plans/2026-06-20-v11-dag-router-rebuild.md` § L6 side-DAG filler
- Companion finding: `findings/deps-audit-2026-06-20-phenoResearchEngine.md`
- Companion finding: `findings/2026-06-20-sd-sota-04-deprecation.md`

---

**Effective date:** 2026-06-20
**Expiry of compatibility shim:** 2026-09-18 (90 days)
**Final disposition:** repository will be archived and PyPI package will be marked deprecated in the next release cycle.
