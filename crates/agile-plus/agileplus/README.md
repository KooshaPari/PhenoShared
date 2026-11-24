# AgilePlus

[![GitHub Actions](https://github.com/KooshaPari/AgilePlus/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/KooshaPari/AgilePlus/actions)

AgilePlus is a polyglot monorepo implementing a next-generation project management platform with hexagonal architecture, event sourcing, multi-VCS support, and an MCP-native agent surface.

## Architecture

AgilePlus is a multi-language monorepo:

- **Rust workspace** (`rust/`, `libs/`, `crates/`) — domain core, gRPC stubs (`agileplus-proto`), and supporting libraries (`nexus`, `intent-registry`, `health-monitor`, `hexkit`, `xdd-lib-rs`, plugin adapters for git/grpc/cli/integration). Hexagonal/ports-and-adapters with event sourcing and a hash-chained evidence ledger.
- **Python layer** (`python/`, `agileplus/`, `agileplus-mcp/`) — MCP server, traceability tooling, and the `agileplus` CLI used for spec-driven workflows.
- **TypeScript / Web** (`apps/landing`, `.vitepress/`) — landing site and VitePress docsite.
- **Go** — tooling slots reserved (none currently active in `apps/`).
- **Protocol** (`proto/`, `buf.yaml`, `buf.gen.yaml`) — gRPC contract definitions consumed by `agileplus-proto`.
- **Specs & governance** (`kitty-specs/`, `docs/specs/`, `docs/agents/`) — spec-driven development inputs (work packages, prompts, ADRs).

Stack summary: Rust (Axum, Tonic/gRPC, SQLite) + Python (MCP, FastAPI-style tooling) + TypeScript (VitePress) + Plane.so / GitHub / NATS integrations.

## Quick Start

```bash
# Rust workspace (lives under rust/)
cd rust && cargo build
cd rust && cargo test
cd rust && cargo clippy --all
cd rust && cargo fmt --all

# gRPC stubs (requires buf)
buf generate

# Python MCP server
cd agileplus && python -m agileplus

# Landing site
cd apps/landing && npm install && npm run dev
```

Toolchain is pinned via `rust-toolchain.toml` and `.mise.toml`. Pre-commit hooks live in `.pre-commit-config.yaml`.

## Branch Discipline

`main` is protected. All work flows through pull requests:

1. Branch from `main` using a descriptive prefix (`feat/`, `fix/`, `docs/`, `chore/`).
2. Commit changes locally; never push directly to `main`.
3. Open a PR with `gh pr create`; wait for review and CI before merging.
4. Feature work happens in isolated worktrees under `repos/AgilePlus-wtrees/<topic>/` (see `Phenotype/CLAUDE.md`).
5. The canonical `repos/AgilePlus` checkout stays on `main` and is used only for pulls and merge integration.

## Deeper Context

- **Agent governance:** `docs/agents/governance-constraints.md`
- **Prompt format:** `docs/agents/prompt-format.md`
- **ADRs:** `docs/adr/`
- **Feature specs:** `docs/specs/`, `kitty-specs/`
- **Workspace operating notes:** `Phenotype/CLAUDE.md` (parent), `~/.claude/CLAUDE.md` (global)

## Bootstrap Checklist

Repository hygiene baseline (Phenotype-org standard):

- [ ] **trufflehog** secret scanning configured (`.pre-commit-config.yaml` already wires it; verify CI workflow exists under `.github/workflows/`).
- [ ] **`.github/FUNDING.yml`** populated with sponsorship targets.
- [ ] **`SECURITY.md`** with disclosure contact and supported versions.
- [ ] **`.github/dependabot.yml`** for cargo / pip / npm / github-actions ecosystems.
- [ ] **`deny.toml`** present (already shipped) and exercised by `cargo deny check` in CI.
- [ ] **`gitleaks.toml`** present (already shipped); ensure CI invokes it.
- [ ] **SBOM**: `sbom.cdx.json` regenerated on release.
- [ ] **Branch protection** on `main`: required PR reviews, signed commits, linear history.

## License

See individual crates for license metadata. Generated gRPC stubs (`rust/agileplus-proto`) are MIT.
