---
spec_id: eco-009
plan_status: NOT_STARTED
---

# Plan — Deploy Markers

## Objective

Close the 60/61 deploy-marker gap across the Phenotype fleet by adding a standardized `docs/deployment.md` to every active repo, and gate the ecosystem health scan's deploy-surface metric on marker presence.

## Scope

**In scope**: 60 repositories currently missing `docs/deployment.md`, the standard template, the health-scan gate update, and the per-repo worklog.

**Out of scope**: rewriting existing deployment prose, CI workflow changes, secrets rotation, and any non-`docs/deployment.md` deploy artifacts.

## Implementation Steps

1. **Marker audit** — Run a filesystem sweep across `repos/` to enumerate which repos already have `docs/deployment.md` and which are missing. Produce a JSON map of `{ repo: present|missing|excluded }` and persist to `worklogs/deploy-marker-scaffold-20260605.json`.
2. **Fan-out scaffold (gated on disk)** — When disk budget allows, dispatch parallel sub-agents to add the standard `docs/deployment.md` (see template) to each missing repo in its own `repos/<repo>-wtrees/deploy-marker/` worktree. Without worktrees, write the file in place; defer git operations.
3. **Progress tracking** — Update `worklogs/deploy-marker-scaffold-20260605.json` after each batch with timestamps, author, repo, and status. The worklog is the single source of truth until the scan reports 61/61.
4. **Health-scan integration** — Patch the deploy-surface metric to require `docs/deployment.md` (or a justified exclusion file) before reporting a repo as confirmed. This is the gate that prevents regression to the 1/61 state.
5. **Verification** — Re-run the audit, re-run the health scan, confirm 61/61 confirmed (or 61/61 with all missing entries explicitly excluded), and write the final worklog snapshot.

## Verification

- `agileplus scan deploy-surface` reports 61/61 confirmed.
- `worklogs/deploy-marker-scaffold-20260605.json` shows every repo with a terminal status.
- A spot-check of three random `docs/deployment.md` files confirms the template sections are present and the file parses as valid UTF-8.
- The health-scan gate change is covered by a unit test asserting a repo without the marker is not counted as confirmed.
