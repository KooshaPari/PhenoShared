---
created: 2026-06-05T00:00:00Z
created_at: 2026-06-05
slug: eco-016-lint-hygiene
spec_id: eco-016
state: PENDING
status: active
superseded_by: null
title: Lint Hygiene
type: operational
---
# eco-016: Lint Hygiene

## Problem

`cargo build` and `cargo test` over the FocalPoint workspace emit rustc warnings that violate the zero-warning policy declared in `clippy.toml` and the quality gate enforced by `task quality`. Current session surfaced:

- **Unused variables**: `pages`, `client`, `rules`, `task_store`, `uuid`, `demo_task_count`.
- **Dead code**: `mock_github_pr_closed_event`, `MockAuditStore`.
- **Non-snake-case**: `missing_celebrations_heuristic_detects_unCelebrated_tasks`.

These warnings degrade build logs, mask new warnings, and break `cargo clippy --all -- -D warnings`.

## Target Users

- **FocalPoint maintainers** — need a clean warning surface so CI and local `task quality` pass deterministically.
- **Phenotype agents** — sweep output must not be drowned by pre-existing lint debt.

## Functional Requirements

FR-1. Establish a zero-warning policy for `cargo build` and `cargo test` across the workspace.

FR-2. For each unused variable in the list above, either prefix with `_` (when the binding is part of a signature or trait) or remove the binding entirely (when unused locally).

FR-3. Remove the dead-code items `mock_github_pr_closed_event` and `MockAuditStore` from the codebase, or annotate them with `#[allow(dead_code)]` only when a concrete tracking reference is recorded in this spec.

FR-4. Rename `missing_celebrations_heuristic_detects_unCelebrated_tasks` to a snake_case identifier (`missing_celebrations_heuristic_detects_uncelebrated_tasks`) and update every call site.

## Acceptance Criteria

AC-1. `cargo build --workspace` reports 0 warnings on the default feature set.

AC-2. `cargo test --workspace --no-run` reports 0 warnings.

AC-3. `cargo clippy --all -- -D warnings` exits 0.

AC-4. `task quality` exits 0 from the repo root.

## Constraints

- **No new warnings introduced**: any fix must not add `#[allow(...)]` annotations without a documented justification and tracking reference.
- **Disk full**: this spec produces writes only, no git operations or worktree creation.
- **Single-batch execution**: do not run parallel builds; one `cargo build`/`cargo test`/`cargo clippy` invocation per verification step.
- **Snake-case rename must update call sites**: do not leave stale references to the camelCase identifier.
