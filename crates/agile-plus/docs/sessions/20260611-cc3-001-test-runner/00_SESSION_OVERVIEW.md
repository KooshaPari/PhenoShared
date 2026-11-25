# Session Overview

- Session: `CC3-001`
- Goal: add workspace-wide Just targets for `test`, `test-unit`, and `test-integration`.
- Success criteria:
  - `Justfile` exposes all three targets.
  - `test-unit` runs workspace Rust tests.
  - `test-integration` runs the dedicated integration crate with its gated feature and ignored tests enabled.
  - Contributor docs point to the real targets.

# Key Decisions

- Keep `test-unit` on `cargo test --workspace --all-features` to preserve the current broad Rust workspace coverage.
- Make `test` the aggregate entrypoint so callers can run the full supported test surface from one Just target.
- Use the dedicated `agileplus-integration-tests` crate for `test-integration`, but invoke it through `--manifest-path` because the crate is present on disk without being listed in the root workspace members.
- Add `crates/agileplus-integration-tests` to the root workspace members so Cargo can execute the integration crate from the repo root without workspace errors.
