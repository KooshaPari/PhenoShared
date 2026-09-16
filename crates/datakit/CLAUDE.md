# DataKit — CLAUDE.md

---

## Project Overview

| Field | Value |
|-------|-------|
| Name | DataKit |
| Crate | `datakit` |
| Edition | 2024 |
| Rust version | stable |
| License | MIT |
| Status | Planning (pre-alpha) |
| Owner | Phenotype org |

## Stack

| Layer | Technology |
|-------|------------|
| Language | Rust |
| Testing | `cargo test`, `cargo nextest` |
| Linting | `clippy` |
| Formatting | `rustfmt` |
| Dependency audit | `cargo-deny` (configured in `deny.toml`) |
| CI | GitHub Actions (`ci.yml`) |

## Key Commands

```bash
# Build
cargo build

# Test
cargo test

# Format
cargo fmt --check

# Lint
cargo clippy --all-targets -- -D warnings

# Full quality gate
cargo fmt --check && cargo clippy --all-targets -- -D warnings && cargo test
```

## Source Map

```
src/
├── lib.rs          # DataStream<T>, Pipeline<T, U>
tests/
├── pipeline_test.rs # Pipeline transformation tests
```

## Quality Gates

- `cargo fmt --check` — formatting must pass
- `cargo clippy --all-targets -- -D warnings` — zero lints allowed
- `cargo test` — all tests must pass
- `cargo deny check` — dependency audit (if `deny.toml` is configured)

## CI / GitHub Actions

- `ci.yml` runs build and test on every PR targeting `main`
- Branch protection requires CI pass on `main`

## Git Workflow

```
origin  = KooshaPari/DataKit   (main repo)
```

## Security & Compliance

- Dependency audit via `cargo-deny` (when configured)
- `gitleaks` secret scanning via pre-commit hooks
- Vulnerability reporting via GitHub Security Advisories

## Community Files

- `README.md` — project overview and quickstart
- `CONTRIBUTING.md` — development setup and submission guidelines
- `SECURITY.md` — vulnerability reporting policy
- `CODE_OF_CONDUCT.md` — Contributor Covenant v2.1
- `CHANGELOG.md` — notable changes
- `CODEOWNERS` — review assignments
- `.editorconfig` — editor settings
- `.pre-commit-config.yaml` — pre-commit hooks
- `.mergify.yml` — automated PR management
