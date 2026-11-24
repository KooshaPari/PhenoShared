# eco-016: Lint Hygiene — Tasks

| WP | Title | Description | Depends On | Est. Tool Calls |
|----|-------|-------------|------------|-----------------|
| WP-01 | Fix unused variables | Prefix with `_` or remove `pages`, `client`, `rules`, `task_store`, `uuid`, `demo_task_count` | — | 4 |
| WP-02 | Remove dead code | Delete `mock_github_pr_closed_event` and `MockAuditStore` (or annotate with justification) | — | 3 |
| WP-03 | Rename to snake_case | Rename `missing_celebrations_heuristic_detects_unCelebrated_tasks` → `..._uncelebrated_tasks` and update call sites | — | 3 |
| WP-04 | Verify zero warnings | Run `cargo build`, `cargo test --no-run`, `cargo clippy --all -- -D warnings`, `task quality`; confirm 0 warnings | WP-01, WP-02, WP-03 | 4 |
