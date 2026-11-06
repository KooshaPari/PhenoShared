# Testing Strategy

## Planned Checks

- `git diff --check` passed.
- README badge search with `rg` passed.
- `cargo fmt --all --check` reports pre-existing Rust formatting drift outside
  this README/session-doc change.
- `cargo clippy --workspace --offline -- -D warnings` passed.
- `cargo test --workspace --offline` passed with 43 tests.
- `task build` passed.

## Scope

This is a README/session-doc governance refresh. Failures from unrelated
pre-existing source, missing cached dependencies, or sandbox limits are recorded
as blockers rather than broadened into this change.
