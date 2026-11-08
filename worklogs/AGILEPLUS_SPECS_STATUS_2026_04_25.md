# AgilePlus kitty-specs Status Audit — 2026-04-25

**Project:** [AgilePlus] · **Category:** GOVERNANCE · **Scope:** product-DAG-extension audit
**Source:** `/Users/<REDACTED>/CodeProjects/Phenotype/repos/AgilePlus/kitty-specs/`
**Method:** Read-only state extraction from `spec.md` frontmatter + `git log` first/last commit dates.

---

## Summary

- **Total active specs:** 37 (excludes `kitty-specs/archive/` which holds 005, 006, 007)
- **Archived specs:** 3 (heliosapp-completion, helioscli-completion, thegent-completion)
- **All 37 specs touched 2026-04-25** (today's backfill session re-stamped every dir)
- **Genuinely new specs created today:** 2 (`oci-lottery-daemon`, `oci-post-acquire-hooks`)

## State Distribution

| State | Count | % |
|-------|-------|---|
| IN_PROGRESS | 19 | 51% |
| DEFERRED | 14 | 38% |
| DONE | 3 | 8% |
| (no spec.md / template) | 1 | 3% |
| **TOTAL** | **37** | 100% |

## Plan/Tasks Coverage

| Coverage | Count |
|----------|-------|
| Has plan.md AND tasks.md | 16 |
| Has plan.md only | 9 |
| Has tasks.md only | 2 |
| Neither | 10 |

---

## Ready to Implement (planned/in-progress + plan + tasks)

Specs with `IN_PROGRESS` state, both `plan.md` and `tasks.md` present:

1. `001-spec-driven-development-engine` (2026-03-29)
2. `002-org-wide-release-governance-dx-automation` (2026-03-29)
3. `013-phenotype-infrakit-stabilization` (2026-04-02)
4. `014-observability-stack-completion` (2026-04-02)
5. `016-agent-framework-expansion` (2026-04-02)

## In Flight (IN_PROGRESS)

19 total. Of these, 5 are above (fully scaffolded). The remaining 14 lack tasks.md or plan.md:

- `eco-001-worktree-remediation`, `eco-002-branch-consolidation`, `eco-003-circular-dep-resolution`,
  `eco-004-hexagonal-migration`, `eco-005-xdd-quality`, `eco-006-governance-sync`
  (all six: spec only, no plan/tasks — stub-grade)
- `<REDACTED>-stale-repo-triage` (plan, no tasks)
- `phenosdk-decompose-core` (plan, no tasks)
- `phenosdk-decompose-llm` (spec only)
- `phenosdk-decompose-mcp` (plan, no tasks)
- `phenosdk-wave-a-contracts` (plan, no tasks)
- `portfolio-audit-<REDACTED>-2026` (plan, no tasks)
- `snyk-phase-1-deploy` (spec only)
- `thegent-dotfiles-consolidation` (spec only)

## Stalled

Definition: not DONE, no real activity since creation (creation date ≥30 days ago, today's touch is backfill-only).

All 35 non-DONE specs created on 2026-03-29 / 2026-03-31 / 2026-04-01 / 2026-04-02 are technically stalled by the strict-30-day rule (today's `2026-04-25` touch is metadata backfill, not implementation).

Highest-priority stalled (IN_PROGRESS, no implementation evidence in history):
- `001-spec-driven-development-engine` (27 days, scaffolded but unimplemented)
- `002-org-wide-release-governance-dx-automation` (27 days)
- `013-phenotype-infrakit-stabilization` (23 days)
- `014-observability-stack-completion` (23 days)
- `016-agent-framework-expansion` (23 days)
- All `eco-00*` (27 days, stub-grade)
- All `phenosdk-*` (27 days, partial scaffolding)

## Backfill (created or wholly authored 2026-04-25)

Created today:
- `oci-lottery-daemon` (DEFERRED, no plan, no tasks)
- `oci-post-acquire-hooks` (DEFERRED, no plan, no tasks)

Re-stamped today (metadata/state backfill, no new artifacts): all 35 other specs.

## Done

- `003-agileplus-platform-completion`
- `codeprojects-archive-manifest`
- `feature-specification-template-platform-completion`

## Recommended Next 3 Specs for Implementation

Selection rule: `IN_PROGRESS` + `plan.md` + `tasks.md` + highest leverage on the active product DAG.

1. **`013-phenotype-infrakit-stabilization`** — unblocks the shared-infra layer everyone else (eco-*, observability, agent-framework) depends on. Highest cascading payoff.
2. **`014-observability-stack-completion`** — Sentry/Snyk Phase 1 deployed but completion gates (Prometheus, dashboards) sit here; pairs with snyk-phase-1-deploy.
3. **`016-agent-framework-expansion`** — direct enabler for thegent-dispatch + cheap-llm wiring already validated in 2026-04-22 session; ready to extend now that quiescent fleet allows focused work.

Runner-ups (also fully scaffolded): `001-spec-driven-development-engine`, `002-org-wide-release-governance-dx-automation` — high value but broader scope, defer until after the three above land.

---

## Notes & Caveats

- All 37 dirs share `last-touch=2026-04-25` because of today's backfill commit; treat last-touch as unreliable until next genuine edit.
- 14 IN_PROGRESS specs are stub-grade (no plan, no tasks). They are work intent, not work plan — needs `/spec-kitty.plan` + `/spec-kitty.tasks` before implement.
- `022-batch13-repo-remediation` has tasks.md but no plan.md — anomalous; recommend running `/spec-kitty.plan`.
- `kitty-specs/archive/` (005, 006, 007) excluded from active counts; those tracked Helios family completion now-released (see release commit `6a6a4b2b8`).
