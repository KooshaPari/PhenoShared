# Specifications

## Acceptance Criteria

- Current-head root README contains the Sladge badge.
- Session docs record the superseded stale branch and current evidence.
- Validation covers diff hygiene, badge presence, and repo-local task gates or
  records exact blockers.
- Canonical checkout remains unchanged unless full integration is safe.

## Assumptions, Risks, Uncertainties

- Assumption: current local `main` is the right evidence base because the
  canonical checkout has moved beyond the older detached/prepared evidence.
- Risk: stale `aa66c86` evidence could be mistaken as current.
- Mitigation: record the new worktree, branch, and commit in downstream and
  projects-landing ledgers.
