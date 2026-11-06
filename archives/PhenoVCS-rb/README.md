<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->

![Downloads](https://img.shields.io/github/downloads/KooshaPari/PhenoVCS/total?style=flat-square&label=downloads&color=blue)
![GitHub release](https://img.shields.io/github/v/release/KooshaPari/PhenoVCS?style=flat-square&label=release)
![License](https://img.shields.io/github/license/KooshaPari/PhenoVCS?style=flat-square)
![AI-Slop](https://img.shields.io/badge/AI--DD-Slop%20Expected-orange?style=flat-square)
![AI-Only-Maintained](https://img.shields.io/badge/Planned%20%26%20Maintained%20by-AI%20Agents%20Only-red?style=flat-square)
![HITL-less](https://img.shields.io/badge/HITL--less%20AI--DD-metaproject-yellow?style=flat-square)

> ⚠️ **AI-Agent-Only Repository**
>
> This repo is **planned, maintained, and managed exclusively by AI Agents**.
> Slop issues, rough edges, and AI artifacts are **expected and intentionally
> present** as part of an **HITL-less / minimized AI-DD** metaproject focused
> on learning, refining, and brute-force training both the agents and the
> human operator. Bug reports and contributions are still welcome, but please
> expect AI-generated code, comments, and documentation throughout.

<!-- AI-DD-META:END -->

## Work State

| Field       | Value                                                                      |
| ----------- | -------------------------------------------------------------------------- |
| Last commit | 2026-07-18 (airlock-v2 WIP + T0 core/airlock)                              |
| Open issues | see GitHub                                                                 |
| Branch      | `feat/a-plus-t0-core-airlock` (airlock WIP base)                           |
| Focus       | T0 — workspace honesty + `pheno-vcs-core` start; airlock-v2 not yet landed |

Progress: ██░░░░░░░░ ~20% (scaffolding + airlock WIP — not hygiene-complete)

> Honest status: core crates exist; `pheno-vcs-core` now has shared types/traits;
> `ports/` is a workspace member (multi-backend Vcs stubs); `airlock-v2` is vendored
> but still WIP. Integration tests and an airlock land PR are T1+.

> **Pinned references (Phenotype-org)**
>
> - MSRV: see rust-toolchain.toml
> - cargo-deny config: see deny.toml
> - cargo-audit: rustsec/audit-check@v2 weekly
> - Branch protection: 1 reviewer required, no force-push
> - Authority: phenotype-org-governance/SUPERSEDED.md

# PhenoVCS

[![Build](https://img.shields.io/github/actions/workflow/status/KooshaPari/PhenoVCS/ci.yml?branch=main&label=build)](https://github.com/KooshaPari/PhenoVCS/actions)
[![Release](https://img.shields.io/github/v/release/KooshaPari/PhenoVCS?include_prereleases&sort=semver)](https://github.com/KooshaPari/PhenoVCS/releases)
[![License](https://img.shields.io/github/license/KooshaPari/PhenoVCS)](LICENSE)
[![Phenotype](https://img.shields.io/badge/Phenotype-org-blueviolet)](https://github.com/KooshaPari)
[![AI Slop Inside](https://sladge.net/badge.svg)](https://sladge.net)

Version control primitives registry for the Phenotype ecosystem — git worktree management, VCS abstractions, and the concurrency-safe primitives Phenotype agents rely on when they check out, branch, commit, and integrate code.

**Part of the [Phenotype org](https://github.com/KooshaPari) ecosystem.** Shares CI reusables and conventions with [phenoShared](https://github.com/KooshaPari/phenoShared). Follows org conventions: conventional commits, `<type>/<topic>` branching, Apache-2.0 + MIT dual license.

## What it does

Phenotype runs many concurrent agents that each need their own safe, reproducible working tree. PhenoVCS encapsulates the rules — worktree creation and teardown, branch discipline, integration-mode detection, lock coordination — so every agent runtime enforces the same VCS behaviors instead of reimplementing `git` shell-outs.

The crates here are consumed by agent dispatchers, the Phenotype daemon, and higher-level spec-driven workflows that spawn per-feature worktrees (`repos/<repo>-wtrees/<topic>`).

## Status

**Active — early scaffolding + airlock WIP.** `pheno-vcs-core` exports shared types
(`VersionedPath`, `VcsError`, thin ports); `worktree-manager` is hexagonal and
consumes core; `ports/` holds multi-backend `Vcs` stubs; `airlock-v2` is vendored
but not released. See [SPEC.md](./SPEC.md), [PLAN.md](./PLAN.md), and [ADR.md](./ADR.md).

## Requirements

- Rust stable (edition 2021)
- `git` 2.40+ on `$PATH` (required for worktree semantics used by `worktree-manager`)

## Quick start

```bash
# Build
cargo build --workspace

# Test
cargo test --workspace

# Lint
cargo clippy --workspace --all-targets -- -D warnings

# Format
cargo fmt --all -- --check
```

Add a crate as a git dependency:

```toml
[dependencies]
pheno-vcs-core     = { git = "https://github.com/KooshaPari/PhenoVCS" }
worktree-manager   = { git = "https://github.com/KooshaPari/PhenoVCS" }
```

## Structure

```
crates/
  pheno-vcs-core/      # Shared VCS types/traits (VersionedPath, VcsError, …)
  worktree-manager/    # Git worktree lifecycle — create, lock, integrate, prune
  airlock-v2/          # Vendored airlock engine (WIP)
  phenovcs-observability/
  pheno-tracing/
ports/                 # Multi-backend Vcs port + git/jj stub adapters
ADR.md                 # Architecture decision records
SPEC.md                # Formal spec for worktree semantics and invariants
PRD.md                 # Product requirements
PLAN.md                # Roadmap and sequencing
AGENTS.md              # Agent-facing workflow contract
CLAUDE.md              # Claude-agent operating notes
```

## Design principles

- **Worktrees, not branches-in-place.** Every concurrent agent gets an isolated checkout; no shared working trees.
- **Canonical checkouts stay on `main`.** Feature work happens in `<repo>-wtrees/<topic>`, never in the canonical folder.
- **Fail loudly on dirty integration.** Mixed-provenance commits are a policy violation; VCS primitives surface them early.
- **Non-destructive by default.** `git reset --hard`, `git clean -f`, and friends are gated behind explicit opt-in.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md), [AGENTS.md](./AGENTS.md), and [CLAUDE.md](./CLAUDE.md) for the agent-driven workflow. Report security issues per [SECURITY.md](./SECURITY.md).

## License

Dual-licensed under Apache-2.0 OR MIT. See [LICENSE-APACHE](./LICENSE-APACHE) and [LICENSE-MIT](./LICENSE-MIT).
