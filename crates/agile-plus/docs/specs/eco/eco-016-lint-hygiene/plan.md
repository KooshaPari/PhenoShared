# eco-016: Lint Hygiene — Plan

## Objective

Eliminate rustc warnings (unused variables, dead code, non-snake-case) surfaced during the eco-016 session so that `cargo build`, `cargo test`, and `cargo clippy --all -- -D warnings` exit clean.

## Scope

In scope: the specific identifiers listed in `spec.md` (Problem). Out of scope: any unrelated lint debt, refactors, or clippy pedantic rules beyond the zero-warning baseline.

## Implementation Steps

1. **Survey warnings**: run `cargo build --workspace 2>&1 | grep -E '^(warning|error)'` and confirm the six unused-variable, two dead-code, and one non-snake-case items.
2. **Fix unused variables** (WP-01): for each of `pages`, `client`, `rules`, `task_store`, `uuid`, `demo_task_count` — prefix `_` or remove binding at the call site.
3. **Remove dead code** (WP-02): delete `mock_github_pr_closed_event` and `MockAuditStore`; if a downstream test relies on either, port the test to use a live fixture or annotate with `#[allow(dead_code)]` plus a tracking reference.
4. **Rename non-snake-case** (WP-03): rename `missing_celebrations_heuristic_detects_unCelebrated_tasks` → `missing_celebrations_heuristic_detects_uncelebrated_tasks`; update every call site (test names, function definitions, references).
5. **Verify zero warnings** (WP-04): run `cargo build --workspace`, `cargo test --workspace --no-run`, `cargo clippy --all -- -D warnings`, and `task quality`; all must exit 0 with no `warning:` lines.
