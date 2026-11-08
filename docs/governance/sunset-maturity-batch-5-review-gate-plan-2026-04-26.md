# Sunset Maturity Batch 5 Review-Gate Plan - 2026-04-26

## Purpose

Record the current execution gate after `phenoShared` was intentionally tightened to
require one approving review and review-thread resolution. The next work should not
pretend the queue is mergeable; it should separate review-gated PRs from independent
planning and audit lanes.

## Current Open PR Queue

All open PRs are in `<REDACTED>/phenoShared` and are blocked by `REVIEW_REQUIRED`.

| PR | Title | Role | Merge order |
|---|---|---|---|
| `#110` | `fix(config): restore config core validation` | Unblocks focused `phenotype-config-core` validation and removes the workspace syntax blocker discovered during error-contract work. | 1 |
| `#109` | `feat(errors): add dual-interface contracts` | Implements shared Rust/TypeScript error contracts, fixtures, and package/type parity. | 2 |
| `#108` | `chore(gitignore): add .worktrees/ + .claude/worktrees/ entries` | Prevents local worktree container churn from appearing as repo dirt. | 3 |
| `#107` | `fix(crates): add missing description fields to error-core/event-sourcing/health` | Metadata hygiene for shared crates. | 4 |
| `#106` | `fix(readme): document all 16 workspace members` | README inventory hygiene. | 5 |

Rationale for this order:

1. `#110` should land first because it restores the crate-level validation surface.
2. `#109` builds on that validation reality and is the actual dual-interface contract work.
3. `#108` is safe at any point but should land before more local worktree-heavy lanes.
4. `#107` and `#106` are independent metadata/docs hygiene and can land after the code gates.

## Do Not Do

- Do not admin-merge these PRs while the ruleset requires review.
- Do not disable the review rule just to clear the queue.
- Do not enable CODEOWNER review until `phenoShared` has a second write-capable owner
  or team; current CODEOWNERS would self-block maintainer-authored PRs.
- Do not keep opening more `phenoShared` PRs unless they unblock validation or are
  intentionally queued behind the same review gate.

## Next Executable Lanes Without Approval

1. Build a current repo-state ledger for `SUNSET-001`.
2. Generate P0 branch-tip manifests under `worklogs/p0-drift/`.
3. Decide and document `AuthKit/go` policy for `SUNSET-003`.
4. Resolve `Tracera` vs `Tracera-recovered` routing for `SUNSET-011`.
5. Reconcile the forced-adoption spec after `phenoShared#109/#110`:
   - `error-core`: still needs one real consumer after AuthKit and ResilienceKit.
   - `health`: still needs one real consumer after TestingKit plus the pending hwLedger lane.
   - `config-core`: do not claim adoption value until a real consumer exists; treat it as
     extraction-validation, not forced adoption.

## Acceptance For This Gate

- `phenoShared#110` and `#109` each receive one approval and pass required checks.
- `#110` merges before any workspace-wide validation claims are made.
- `#109` merges before any release-prep or consumer migration claims for
  `@phenotype/errors` / `phenotype-error-core`.
- The PhenoKits worklogs stop saying the open PR queue is empty while these PRs are open.
