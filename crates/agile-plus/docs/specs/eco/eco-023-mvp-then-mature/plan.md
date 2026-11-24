# Plan — MVP-Then-Mature

## Objective

Codify and enforce an anti-regression rule across the ecosystem: every feature must reach MVP before it is matured, and neither partially implemented features nor their specs may regress silently. Ship the rule as CI-integrated autograder steps plus a spec-lint policy.

## Scope

In scope:
- `Changes` template requiring per-FR MVP/Mature tags.
- `fr-regression-check` autograder step (reusable task `task fr:check`).
- `spec-lint` step enforcing append-only spec edits with `supersedes:` linkage.
- Dashboard surfacing of per-FR status and regressing PR pointers.
- Quick-start guide for greenfield adoption.

Out of scope:
- Migrating historical FRs to tagged status (handled by eco-018 follow-up).
- Replacing the existing autograder harness.
- Any new CI runners or billing-impacting changes.

## Implementation Steps

1. **Discovery** — Inventory current FR coverage tooling, spec lint, and autograder task shape across repos; identify reuse points (existing diff/coverage utilities, Vale rules, spec frontmatter parsers).
2. **Design** — Define `Changes` template schema, FR-status data model (`none`/`partial`/`MVP`/`Mature`), and `supersedes:` frontmatter contract; publish as an ADR under `docs/changes/`.
3. **Build — autograder** — Implement `task fr:check` wrapping the existing diff/coverage utilities; produce per-FR status JSON consumed by the dashboard. Wire into autograder manifest.
4. **Build — spec-lint** — Add `spec-lint` step enforcing append-only edits and `supersedes:` linkage; reuse frontmatter parser where present.
5. **Build — Changes template** — Author PR template + lint rule for `Changes` section; integrate with PR-bot if available, otherwise as a pre-merge CI check.
6. **Build — dashboard** — Add FR-status panel using existing dashboard tokens; link regressing PRs.
7. **Test/Validate** — Author fixtures: greenfield PR, regressing PR, spec rewrite with/without `supersedes:`, contradictory new spec. Run autograder end-to-end on a sample repo.
8. **Deploy/Handoff** — Publish `docs/guides/quick-start/MVP_THEN_MATURE_QUICK_START.md`; enable the two CI steps in the canonical autograder; record adoption in `ecosystem-status.md`.

## Dependencies (DAG)

| Step | Depends On |
|------|------------|
| 1 Discovery | — |
| 2 Design | 1 |
| 3 Autograder | 2 |
| 4 Spec-lint | 2 |
| 5 Changes template | 2 |
| 6 Dashboard | 3 |
| 7 Validate | 3, 4, 5 |
| 8 Handoff | 6, 7 |
