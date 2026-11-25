# Research

- Existing `.pre-commit-config.yaml` in this worktree was created for L2-033 and included Python, Go, and TypeScript hooks that do not match QC1-001.
- Existing repo conventions in `Justfile` and `CONTRIBUTING.md` use:
  - `cargo fmt --all --check`
  - `cargo clippy --workspace --all-targets --all-features -- -D warnings`
  - `cargo test --workspace --all-features`
- Existing shell scripts in scope are `docs/worklogs/aggregate.sh`, `history_cleanup.sh`, `scripts/regen-index.sh`, and `scripts/quality-gate.sh`.
