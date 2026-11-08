# Spec: Org Sunset Maturity Program

## Objective

Bring the Phenotype repo ecosystem to a mature closeout state after PR queue cleanup:
every repo has a maturity state, local drift has a disposition, shared crates have canonical
homes, governance enforcement matches docs, and archived repos are quiet.

## Functional Requirements

- FR-SUNSET-001: The system of record MUST classify each repo as `ACTIVE`, `MAINTENANCE`, `SUNSET_READY`, `ARCHIVED`, or `QUARANTINE`.
- FR-SUNSET-002: Any repo with large local drift, dirty gitlinks, or ambiguous canonical-home status MUST be `QUARANTINE` until a written disposition exists.
- FR-SUNSET-003: Archived repos MUST have no open PRs and no `.github/dependabot.yml`.
- FR-SUNSET-004: Shared crates MUST have one canonical source repo before forced adoption.
- FR-SUNSET-005: Active repo governance docs MUST match live GitHub rulesets and required checks.
- FR-SUNSET-006: Stale remote branches without open PRs MUST be deleted, recreated, or recorded with a keep reason.
- FR-SUNSET-007: Worklog and governance evidence MUST live in canonical docs with durable links.

## Non-Functional Requirements

- No destructive repo deletion without a separate ADR.
- No force-push/reset in P0 quarantine repos.
- No mixed broad governance/source PRs.
- All cleanup actions must be reversible or ledgered with tip SHA / PR URL / commit URL.

## Scope

In scope:

- GitHub repo and PR state.
- Local repo drift under `/Users/<REDACTED>/CodeProjects/Phenotype/repos`.
- Shared crate canonical-home migration planning.
- Ruleset/governance reconciliation.
- Worklog/doc consolidation.

Out of scope:

- Product feature delivery.
- Deleting GitHub repos.
- Rewriting old history.

## Acceptance Criteria

- Org open PR queue is either empty after two sweeps or every remaining PR has
  a written gate reason, merge order, and next action.
- Every P0 repo has a drift disposition.
- Archived repos checked have no Dependabot configs.
- Canonical shared crate plan is approved and executable.
- Priority active repos have ruleset parity with docs.
