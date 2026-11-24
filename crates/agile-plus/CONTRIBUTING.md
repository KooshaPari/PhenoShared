# Contributing to AgilePlus

Thank you for your interest in contributing! This repository is part of the [Phenotype](https://github.com/KooshaPari) ecosystem.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Pull Request Checklist](#pull-request-checklist)
- [Code Review](#code-review)
- [Reporting Issues](#reporting-issues)
- [License](#license)

## Prerequisites

- **Rust toolchain**: Nightly (see `rust-toolchain.toml`). Install via `mise install` or `rustup`.
- **mise**: Version manager for Rust, Node.js, Python, and Bun — see [mise.jdx.dev](https://mise.jdx.dev).
- **Node.js**: v22 (managed via mise).
- **Bun**: Runtime for frontend tooling and docs.
- **Python**: 3.12 (managed via mise, used for integration scripts).
- **Git** and a GitHub account with access to push branches.

### macOS (Homebrew)

```bash
brew install mise
mise install           # installs all tools from .mise.toml
cargo install cargo-machete  # unused-dependency detection
```

### Linux / Other

```bash
curl https://mise.jdx.dev/install.sh | sh
mise install
```

Then add Rust components:

```bash
rustup component add clippy rustfmt
```

## Development Setup

### 1. Install dependencies

```bash
git clone <your-fork>
cd AgilePlus
mise install           # installs rust, node, bun, python
cargo fetch            # prefetch crate dependencies
```

### 2. Dev stack (optional, for integration testing)

Some features require an external service stack (NATS, MinIO, Neo4j):

```bash
brew bundle --file=Brewfile   # installs nats-server, minio, neo4j, process-compose
task setup                     # builds + creates required directories
task dev                       # starts all services via process-compose
```

### 3. Verify setup

```bash
cargo check                  # workspace compiles
task fmt:check               # formatting is clean
task lint                    # clippy passes (workspace only)
task dep:check               # no unused dependencies
task test                    # unit + integration tests pass
```

## Development Workflow

1. **Spec first.** All non-trivial work must be tracked in [AgilePlus](https://github.com/KooshaPari/AgilePlus). Check for an existing spec under `kitty-specs/` before implementing; otherwise create one with `agileplus specify --title "<feature>"`.
2. **Branch.** Cut feature branches from `main` using the form `<category>/<short-slug>` (e.g. `feat/auth-rotation`, `fix/null-deref`).
3. **Implement.** Follow the existing module layout. Match prevailing code style — do not reformat unrelated files.
4. **Test.** Run `cargo test --all` (or `cargo test -p <crate>` for a single crate). Add unit tests next to the code under test and integration tests under `tests/`. For frontend changes, also run `npm test` in `crates/agileplus-dashboard/web/`.
5. **Quality gates.** Run `cargo fmt --check` and `cargo clippy --all-targets -- -D warnings` before pushing. Run `task python:lint` if Python code was changed.
6. **Commit.** Use conventional-commit style (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`). Keep commits scoped — one logical change per commit.
7. **Pull request.** Open a PR against `main`. Reference the AgilePlus spec ID in the description. Fill the PR template if present.

## Coding Standards

### Rust

- **Edition**: 2024 (nightly). Keep `rust-toolchain.toml` in sync with the team.
- **Formatting**: `cargo fmt` (enforced by CI). 2-space indent, 100-char width.
- **Lints**: All clippy warnings are errors (`-D warnings`). No `#[allow(dead_code)]` without an inline justification comment (see existing suppressions for the pattern).
- **Unsafe**: Forbidden at the workspace level (`[workspace.lints.rust] unsafe_code = "forbid"`). If truly necessary, add an `#[allow(unsafe_code)]` with a detailed safety comment and get maintainer approval.
- **Errors**: Use `thiserror` for library error types; `anyhow` for application-level error handling.
- **Async**: Use `tokio` as the async runtime. Mark `async` traits with `#[async_trait]`.
- **Imports**: Group as: standard library → external crates → workspace crates → current crate modules.
- **Tests**: Unit tests live in a `#[cfg(test)] mod tests` block at the bottom of the source file. Integration tests live in `tests/`.

### Frontend (React / TypeScript)

- **Stack**: React 19, TypeScript (strict), Tailwind CSS v4, Vite.
- **Formatting**: Use the project Prettier config (double quotes, semicolons, trailing commas).
- **Components**: Functional components with explicit `React.FC<Props>` typing. JSDoc with `@example` for non-trivial components.
- **Styling**: Tailwind utility classes via the `cn()` helper from `lib/utils.ts`. Avoid raw CSS files.
- **Types**: Shared prop types in `types/index.ts`. One file per component.
- **Exports**: Named + default export pattern (see `Card.tsx`).
- **Accessibility**: Semantic HTML (`<article>`, `<header>`, `<nav>`, `role="status"`), ARIA labels, keyboard navigation.

### Python

- **Formatting**: Ruff (see `task python:format`).
- **Tests**: pytest (run via `task python:test`).

## Pull Request Checklist

Before submitting a PR, verify each item:

- [ ] **Spec reference**: PR description links to the AgilePlus spec or issue.
- [ ] **Branch name**: Follows `<category>/<short-slug>` convention.
- [ ] **Build**: `cargo check --workspace` passes without errors.
- [ ] **Lints**: `cargo clippy --all-targets -- -D warnings` is clean.
- [ ] **Formatting**: `cargo fmt --all -- --check` passes (no formatting diffs).
- [ ] **Tests**: `cargo test --workspace` passes. New code has tests.
- [ ] **Unused deps**: `cargo machete` reports no unused dependencies (run `task dep:check`).
- [ ] **No new dead_code suppressions**: If you added `#[allow(dead_code)]`, it has an inline comment explaining why.
- [ ] **Python**: `task python:lint` passes (if Python files changed).
- [ ] **Frontend**: `npm run build` in `crates/agileplus-dashboard/web/` succeeds (if web files changed).
- [ ] **Commits**: Conventional-commit style, one logical change per commit.
- [ ] **PR size**: Keep PRs focused — preferably under 500 lines of meaningful change. Large features should be broken into multiple PRs.

## Code Review

- All PRs require at least one approving review from a maintainer.
- CI must pass on Linux runners (macOS/Windows runners may be skipped due to org billing constraints).
- Do not introduce new lint suppressions without inline justification.
- Reviewers will verify the PR checklist items above.

## Reporting Issues

- **Bugs and feature requests:** open a GitHub issue with reproduction steps or motivation.
- **Security vulnerabilities:** see [`SECURITY.md`](./SECURITY.md) — do **not** file public issues for security reports.

## License

By contributing you agree that your contributions will be licensed under this repository's license (see `LICENSE`).
