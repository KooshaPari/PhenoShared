# Testing Strategy

## Planned Checks

- `git diff --check` passed.
- README badge search with `rg` passed.
- `cargo fmt --all --check` blocked during Cargo metadata loading.
- `cargo clippy --workspace --offline -- -D warnings` blocked during Cargo
  metadata loading.
- `cargo test --workspace --offline` blocked during Cargo metadata loading.
- `task build` blocked during Cargo metadata loading.

## Scope

This is a README/session-doc governance refresh. Failures from unrelated
pre-existing source, missing cached dependencies, or sandbox limits are recorded
as blockers rather than broadened into this change.
