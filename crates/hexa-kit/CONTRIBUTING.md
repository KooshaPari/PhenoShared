# Contributing to HexaKit

Thank you for your interest in contributing! This repository is part of the
[Phenotype](https://github.com/KooshaPari) ecosystem.

## Prerequisites

- Rust toolchain (stable; see `rust-toolchain.toml` if present).
- `just` (task runner: <https://github.com/casey/just>).
- `cargo-deny`, `cargo-audit`, `cargo-machete` (installed via `cargo install --locked`).
- Git and a GitHub account with access to push branches.

## Development Workflow

1. **Spec first.** All non-trivial work must be tracked in
   [AgilePlus](https://github.com/KooshaPari/AgilePlus). Check for an existing
   spec under `kitty-specs/` before implementing; otherwise create one with
   `agileplus specify --title "<feature>"`.
2. **Branch.** Cut feature branches from `main` using the form
   `<category>/<short-slug>` (e.g. `feat/auth-rotation`, `fix/null-deref`,
   `chore/tier-0-hygiene`).
3. **Implement.** Follow the existing module layout. Match prevailing code
   style — do not reformat unrelated files.
4. **Test.** Run `just test` (or `cargo test --workspace`). Add unit tests
   next to the code under test and integration tests under `tests/`.
5. **Quality gates.** Run `just lint` (or `cargo clippy --workspace --all-targets -- -D warnings`
   plus `cargo fmt --all -- --check`) before pushing.
6. **Audit.** Run `just audit` and `just deny` to ensure no new advisories or
   license violations.
7. **Commit.** Use [conventional-commit](https://www.conventionalcommits.org/)
   style (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`). Keep commits
   scoped — one logical change per commit.
8. **Pull request.** Open a PR against `main`. Reference the AgilePlus spec ID
   in the description. Fill the PR template.

## Local quick-start

```sh
just --list          # show all available recipes
just build           # cargo build --workspace
just test            # cargo test --workspace
just lint            # clippy + fmt --check
just ci              # full local CI sweep
```

## Code Review

- All PRs require at least one approving review.
- CI must pass on Linux runners (macOS/Windows runners may be skipped due to
  org billing constraints).
- Do not introduce new lint suppressions without inline justification.
- Public API changes require an ADR entry under `docs/adr/`.

## Reporting Issues

- **Bugs and feature requests:** open a GitHub issue with reproduction steps
  or motivation.
- **Security vulnerabilities:** see [`SECURITY.md`](./SECURITY.md) — do **not**
  file public issues for security reports.

## License

By contributing you agree that your contributions will be licensed under this
repository's license (see `LICENSE`).
