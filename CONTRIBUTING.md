# Contributing to Phenotype Infra

First off, thank you for considering contributing to **Phenotype Infra** — it's
people like you who make this project better for everyone. Phenotype Infra is a
Rust-based compute/infrastructure monorepo providing 3-tier isolation
(WASM, gVisor, Firecracker) and is part of the
[Phenotype](https://github.com/KooshaPari) ecosystem.

This is the canonical contributor guide. It supersedes the shorter
`CONTRIBUTING.md` you may have seen on older branches (which had
copy-paste terminal escape codes that made the rendered Markdown
unreadable). For agent-specific operating procedures, see `AGENTS.md`
and `CLAUDE.md` in this repo.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Project Layout](#project-layout)
3. [Prerequisites](#prerequisites)
4. [Development Setup](#development-setup)
5. [Build](#build)
6. [Test](#test)
7. [Lint, Format, and Quality Gates](#lint-format-and-quality-gates)
8. [Coverage](#coverage)
9. [Commit Message Format (Conventional Commits)](#commit-message-format-conventional-commits)
10. [Branch and PR Process](#branch-and-pr-process)
11. [Code Review](#code-review)
12. [Reporting Issues](#reporting-issues)
13. [Security Disclosures](#security-disclosures)
14. [License](#license)

---

## Code of Conduct

By participating, you agree to abide by the [Phenotype Code of
Conduct](https://github.com/KooshaPari/phenotype-org-governance/blob/main/CODE_OF_CONDUCT.md).
Be respectful. Assume good intent. Keep technical disagreement on the
technical merits.

## Project Layout

```
phenotype-infra/
├── crates/
│   ├── nanovms-core/     # NVMS Go core — C static archive
│   ├── nvms-ffi/          # Rust FFI bindings to NVMS Go Core
│   ├── pheno-compose/     # High-level Rust driver
│   └── pheno-config/      # Shared configuration
├── tests/                 # Cross-crate integration tests
├── docs/                  # ADRs, scorecards, governance
├── scripts/               # Repository automation
├── .github/
│   └── workflows/         # CI, scorecard, audit, quality gates
├── CODEOWNERS             # Root-level ownership alias
├── CONTRIBUTING.md        # This file
├── Cargo.toml             # Workspace manifest
├── Cargo.lock
└── LICENSE
```

## Prerequisites

- **Rust** 1.75+ (install via [rustup](https://rustup.rs/))
- **Cargo** (bundled with Rust)
- **git** 2.40+
- **Go** 1.23+ (only for `nanovms-core` build)

Verify your toolchain:

```bash
rustc --version    # rustc 1.75+
cargo --version    # cargo 1.75+
go version         # go version go1.23 (only for native NVMS build)
git --version
```

## Development Setup

```bash
# 1. Clone
git clone https://github.com/KooshaPari/nanovms.git
cd nanovms

# 2. Fetch Go deps
go mod download

# 3. Install Node deps (docs only)
pnpm install        # or: bun install

# 4. Verify the workspace builds
go build ./...

# 5. Run a smoke test
go test ./... -run TestSmoke
```

### Recommended shell aliases

```bash
alias pi='cd /path/to/phenotype-infra'
alias pitest='cargo test --workspace'
alias pibuild='cargo build --workspace'
```

## Build

Phenotype Infra is a Rust workspace.  The `nvms-ffi` crate includes
inline C shims so the workspace compiles without a Go toolchain.

```bash
# Full workspace
cargo build --workspace

# Single crate
cargo build -p nvms-ffi
cargo build -p pheno-compose-driver

# Release
cargo build --release
```

## Test

```bash
# Unit + integration (workspace)
cargo test --workspace

# Single crate
cargo test -p pheno-compose-driver

# Specific test
cargo test -p pheno-compose-driver -- test_driver_initialization

# With output
cargo test -- --nocapture
```

## Lint, Format, and Quality Gates

```bash
# Format (dprint)
dprint check

# Format and fix
dprint fmt

# Clippy lint
cargo clippy --workspace -- -D warnings

# Pre-commit (gitleaks + dprint + clippy)
pre-commit run --all-files
```

CI runs the same set plus `scorecard` and `codeql` workflows weekly.

## Coverage

```bash
# Coverage using cargo-tarpaulin
cargo tarpaulin --workspace --out Html --output-dir coverage/

# Per-crate summary
cargo tarpaulin --workspace --out Stdout
```

Coverage target is **≥ 60%** for library crates. Drops below 50% need
a PR-body justification.

## Commit Message Format (Conventional Commits)

Phenotype Infra uses [Conventional Commits 1.0.0](https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <short summary>

<body — wrap at 72 columns>

<footer>
```

### Allowed types

| Type       | Purpose                                                  |
|------------|----------------------------------------------------------|
| `feat`     | New user-visible feature                                 |
| `fix`      | Bug fix                                                  |
| `docs`     | Documentation only                                       |
| `style`    | Formatting (no logic change)                             |
| `refactor` | Code restructure (no behavior change)                   |
| `perf`     | Performance improvement                                  |
| `test`     | Adding or fixing tests                                   |
| `build`    | Build system / dependency change                         |
| `ci`       | CI configuration                                         |
| `chore`    | Maintenance, tooling, governance                         |
| `revert`   | Revert a previous commit                                 |

### Scopes (recommended)

`nvms-ffi`, `pheno-compose`, `pheno-config`, `nanovms-core`, `cli`,
`driver`, `docs`, `ci`, `governance`.

### Examples

```
feat(driver): add firecracker instance with snapshot resume

fix(nvms-ffi): null-check pointer before deref in status()

docs(errors): add doc comments to Error variants

chore(governance): add CODEOWNERS, CONTRIBUTING, SECURITY (L20 #30)
```

### Breaking changes

```
feat(api)!: rename Instance.create to Instance.spawn

BREAKING CHANGE: callers must use `.spawn()` instead of `.create()`.
Migration: rg '\.create\(' --type rust | xargs sed -i 's/\.create(/.spawn(/g'
```

## Branch and PR Process

### Branch naming

- `feat/<short-kebab>` — new feature
- `fix/<short-kebab>` — bug fix
- `chore/<short-kebab>` — maintenance, deps, governance
- `docs/<short-kebab>` — documentation
- `refactor/<short-kebab>` — code restructure
- `hotfix/<short-kebab>` — urgent production fix

### Workflow

1. **Branch** off `main`:
   ```bash
   git checkout main && git pull
   git checkout -b feat/your-feature
   ```
2. **Develop** in small, focused commits.
3. **Run the full quality gate** locally:
   ```bash
   cargo fmt --check && \
     cargo clippy --workspace -- -D warnings && \
     cargo test --workspace
   ```
4. **Push** and **open a PR** against `main`:
   ```bash
   git push -u origin feat/your-feature
   gh pr create --base main --title "feat(scope): short summary" \
     --body-file .github/PULL_REQUEST_TEMPLATE.md
   ```
5. **Address review** in additional commits (no force-push during
   review).
6. **Squash-merge** via the GitHub UI; the squash commit MUST follow
   conventional-commits format.

### PR requirements (CI will enforce)

- [ ] Title matches `<type>(<scope>): <summary>`
- [ ] Body references the issue / spec (`Closes #123`)
- [ ] At least 1 approving review from a CODEOWNER
- [ ] CI green: `cargo fmt`, `cargo clippy`, `cargo test`,
  `scorecard`
- [ ] Coverage delta documented (or target met)
- [ ] No new `TODO` without a tracking issue

## Code Review

Reviewers should:

- **Be specific** — quote the line, suggest the fix, link the doc.
- **Distinguish** blocking from non-blocking (prefix `[blocking]` or
  `[nit]`).
- **Approve explicitly** — use the GitHub "Approve" button.

Authors should:

- **Respond to every comment** — push a fix or explain why not.
- **Keep the diff small** — split a 1500-line PR into stacked PRs.
- **Self-review first** — read your own diff in the GitHub PR view.

Review SLA: 1 business day for the first round. If a reviewer is
unreachable, ping `@KooshaPari` to reassign.

## Reporting Issues

Use the GitHub issue templates under `.github/ISSUE_TEMPLATE/`. Always
include:

- Phenotype Infra version (`grep version Cargo.toml`)
- OS and architecture (e.g. `Linux x86_64`)
- Rust toolchain (`rustc --version && cargo --version`)
- Reproduction steps (the smallest possible snippet)
- Expected vs. actual behavior
- Relevant logs (enable with `RUST_LOG=debug`)

## Security Disclosures

For sensitive vulnerabilities, **do not open a public issue**. Follow
the process in [`SECURITY.md`](./SECURITY.md). Acknowledgment within
48 hours, triage decision within 7 days.

## License

By contributing, you agree that your contributions will be licensed
under the **MIT OR Apache-2.0** license (dual-licensed, at the option
of downstream consumers). See [`LICENSE`](./LICENSE) for the full text.

---

Questions? Open a discussion at
https://github.com/KooshaPari/phenotype-infra/discussions or reach out to
@KooshaPari on the Phenotype Discord.
