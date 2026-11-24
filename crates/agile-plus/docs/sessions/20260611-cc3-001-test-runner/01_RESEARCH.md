# Research

- Existing `Justfile` already had `test`, but it directly invoked `cargo test --workspace --all-features` and did not expose `test-unit` or `test-integration`.
- `CONTRIBUTING.md` already referenced `just test-integration`, which meant the documentation was ahead of the actual task runner.
- `crates/agileplus-integration-tests/src/lib.rs` documents two modes:
  - unit-safe: `cargo test -p agileplus-integration-tests`
  - full integration: `cargo test -p agileplus-integration-tests --features integration -- --include-ignored`
- The documented `-p agileplus-integration-tests` form does not work from the repo root because the crate was not listed in the root workspace members.
- The integration crate also cannot be run safely through `--manifest-path` while still inheriting `workspace = true` fields; Cargo rejects that mismatch and explicitly recommends adding the crate to `workspace.members`.
- The integration crate defines a dedicated `integration` feature in `crates/agileplus-integration-tests/Cargo.toml`, so the correct fix is to add the crate to the workspace and keep the Just target on the documented feature/ignored-test invocation.
