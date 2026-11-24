# Contributing to HeliosCLI

Thank you for your interest in HeliosCLI. This guide covers the development
workflow, quality bar, and review process. By participating, you agree to abide
by the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Table of Contents

- [Development Setup](#development-setup)
- [Branching and Commits](#branching-and-commits)
- [Local Quality Gate](#local-quality-gate)
- [Pull Requests](#pull-requests)
- [Reporting Bugs](#reporting-bugs)
- [Proposing Features](#proposing-features)
- [Security Issues](#security-issues)
- [License and DCO](#license-and-dco)

## Development Setup

### Prerequisites

- **Rust** stable (see `rust-toolchain.toml`) and `cargo`
- **Bun** ≥ 1.1 (for `codex-cli/` extension surface)
- **Python** ≥ 3.11 (for `heliosBench/` and `helios_router/`)
- **Node.js** ≥ 20 (for docs and TypeScript tooling)
- **Bazel** ≥ 7 (optional, for Bazel-based builds; see `BUILD.bazel`)

### Clone

```bash
git clone https://github.com/KooshaPari/HeliosCLI.git
cd HeliosCLI
```

### First-time install

```bash
just install      # or: cargo fetch
just build        # release build of the primary harness workspace
```

The vendored workspaces (`codex-rs/`, `helios-rs/`) are excluded from the top-level
`Cargo.toml` and have their own roots. To build them use `cd codex-rs && just build`
or `cd helios-rs && cargo build`.

## Branching and Commits

- **Branch from `main`.** Use the form `feat/<slug>-<YYYYMMDD>`,
  `fix/<slug>-<YYYYMMDD>`, or `chore/<slug>-<YYYYMMDD>`.
- **One logical change per branch.** Split unrelated work into separate PRs.
- **Conventional Commit messages.** Use the format `<type>(<scope>): <subject>`
  where `<type>` is one of `feat`, `fix`, `chore`, `docs`, `refactor`, `test`,
  `build`, `ci`, `perf`, `revert`, `style`.
- **Reference the work.** When a commit closes an issue or implements a spec,
  include `Closes #N` or `Refs FR-HELIOS-NNN` in the body.

## Local Quality Gate

Before opening a pull request, run the local quality gate:

```bash
just ci           # fmt + lint + test + build + audit + deny
```

You can also run individual stages:

```bash
just fmt          # cargo fmt --all
just lint         # cargo clippy --all-targets -- -D warnings
just test         # cargo test --all-features  (or cargo nextest run)
just audit        # cargo audit
just deny         # cargo deny check
just build        # cargo build --release
```

CI runs the same recipes on Ubuntu 24.04 with Rust stable.

## Pull Requests

1. **Open an issue first** for non-trivial changes to align on scope and design.
2. **Push your branch** and open a PR using the
   [PR template](./.github/PULL_REQUEST_TEMPLATE.md).
3. **Fill out the entire PR description**: summary, changes, testing evidence,
   related issues, FR/spec links.
4. **Pass CI**: all checks must be green before review.
5. **Request review** from `@kooshapari` (see [CODEOWNERS](./.github/CODEOWNERS)).
6. **Address review feedback** in additional commits; squash on merge.

### Review criteria

- Code correctness and adherence to the architecture (see `AGENTS.md`).
- Tests for new behaviour (`cargo test`) and FR traceability comments.
- No new `unwrap()` / `expect()` without a documented invariant
  (`clippy.toml` and `codex-rs` deny them by default).
- SPDX header on every new Rust file: `// SPDX-License-Identifier: MIT OR Apache-2.0`.
- 100-character line length (enforced by `.editorconfig` and `rustfmt.toml`).

## Reporting Bugs

Use the [bug report template](./.github/ISSUE_TEMPLATE/bug_report.md). Include
`helios --version` output, OS/arch, reproduction steps, and full logs.

## Proposing Features

Use the [feature request template](./.github/ISSUE_TEMPLATE/feature_request.md).
Link to a Functional Requirement (`FR-HELIOS-NNN`) or a kitty-spec if one exists.

## Security Issues

**Do not file public issues for security vulnerabilities.** Follow the
[Security Policy](./SECURITY.md) and report privately via GitHub Security
Advisories or email.

## License and DCO

HeliosCLI is dual-licensed under **MIT OR Apache-2.0** (SPDX: `MIT OR Apache-2.0`).
By submitting a contribution, you agree to license it under the same terms.
We do not currently require a DCO sign-off; the SPDX header on each source
file is sufficient.

---

Happy hacking. — `@kooshapari` and contributors
