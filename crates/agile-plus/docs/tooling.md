# Tooling Reference

AgilePlus is a Phenotype-org spec-driven project-management platform. The repo is polyglot: Rust is the long-term workspace scaffold, Python hosts the `dispatch-mcp` MCP server, and Go is present in sibling tooling such as `pheno-cli`. This page is the local tooling map for the repo.

## Overview

- **Rust**: root Cargo workspace is scaffolded for future AgilePlus crates.
- **Python**: `dispatch-mcp/` is a standalone MCP server package.
- **Go**: `pheno-cli/` is a separate CLI in the wider workspace shelf.

For broader repo context, read:

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [AGENTS.md](../AGENTS.md)
- [CLAUDE.md](../CLAUDE.md)

## Existing Tooling

The repo already has the following structure and automation surface:

- `ARCHITECTURE.md` describes AgilePlus as the work-tracking spine for the Phenotype shelf.
- `AGENTS.md` defines the repo-wide commands, quality gates, and branch discipline.
- `CLAUDE.md` adds the protected-main / PR-only workflow and the worktree convention.
- `.github/workflows/` contains the current CI and security jobs.

Use this document as the quick-start index; use the source docs above for policy and deeper context.

## `dispatch-mcp`

`dispatch-mcp/` is a Python MCP server for tier-based dispatch delegation via OmniRoute.

### Package layout

- `dispatch-mcp/pyproject.toml`
- `dispatch-mcp/src/dispatch_mcp/server.py`
- `dispatch-mcp/tests/test_server.py`

### Run

Install in editable mode:

```powershell
cd dispatch-mcp
python -m pip install -e .
```

Start the server via the entry point:

```powershell
dispatch-mcp
```

Or run the module directly:

```powershell
python -m dispatch_mcp.server
```

### Config

- `OMNIROUTE_URL` is required.
- `LOG_LEVEL` is optional.

See `dispatch-mcp/README.md` for the full tool list and runtime constraints.

## CI Workflows

The repo-level GitHub Actions directory is `.github/workflows/`.

Relevant workflows and config:

- `trufflehog.yml` - secrets scanning.
- `semgrep` - Semgrep SAST is wired into the repo security checks in the workflow set.
- `security-guard.yml` - pre-commit guard checks.
- `.github/dependabot.yml` - automated dependency update policy.

Related workflow files currently present in the repo include `ci.yml`, `rust-security.yml`, `cargo-audit.yml`, `cargo-machete.yml`, `sast-quick.yml` (Semgrep), and `quality-gate.yml`.

## Cargo Workspace

The root Rust workspace is scaffolded but not yet populated with first-class source crates.

Current shape:

- Root `Cargo.toml` declares a workspace.
- `crates/` contains scaffolded crate directories.
- There is no populated Rust source tree yet.

To add the first real crate:

1. Create a new crate directory under `crates/`, for example `crates/agileplus-domain/`.
2. Add a `Cargo.toml` with a `[package]` section and workspace-qualified metadata.
3. Add `src/lib.rs` or `src/main.rs`.
4. Make sure the crate name matches the workspace include pattern in the root `Cargo.toml`.
5. Run `cargo test` once the crate has source.

If you are introducing the first shared crate, keep the scope small and avoid pulling in unrelated workspace members until the new crate is stable.

## Testing

- **Python**: run `pytest` under `dispatch-mcp/`.

  ```powershell
  cd dispatch-mcp
  python -m pytest
  ```

- **Rust**: use `cargo test` when the workspace has populated Rust source.

  ```powershell
  cargo test
  ```

For style and quality checks, the repo guidance still applies:

- `cargo fmt --all`
- `cargo clippy --all`
- `ruff check python/`

## Branch Discipline

Follow the branch rules from `CLAUDE.md`:

- Use feature branches with `feat/`, `fix/`, `chore/`, `ci/`, or `docs/` prefixes.
- Keep work in a dedicated worktree, following the `<repo>-wtrees/<subject>/` convention.
- Do not commit directly to `main`.
- Keep PRs small and focused to the owning component.

For AgilePlus specifically, the tracked workspace is `agileplus/` and the canonical repo is protected for PR-based merges only.
