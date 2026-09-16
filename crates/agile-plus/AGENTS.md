# AgilePlus AGENTS.MD

## Project Overview
AgilePlus is the Phenotype-org spec-driven development framework. Rust CLI + workspace for managing specs, work packages, and project governance. CLI: `agileplus <command>`

## Stack
- Language: Rust
- Build: Cargo workspace (members added when source exists; scaffolded crates/libs excluded until populated)
- CLI: Custom typer-based CLI
- Spec storage: `kitty-specs/` (inside the agileplus workspace)

## Key Commands
- `cargo build --release`
- `cargo test`
- `agileplus specify [--feature <slug>] [--from-file <path>] [--force]` — create/revise a feature spec (no `--title` / `--description` flags)
- `agileplus list [--state <state>]` — list features in SQLite (there is no top-level `agileplus status` for WP/product status)
- `agileplus platform status` — service health via PATH wrapper (`.agileplus/platform-status.sh`); Neo4j optional
- There is no `agileplus init` command; SDD starts with `specify` in a git repo

## Quality Gates
- `cargo clippy --all` + `cargo fmt --all`
- `cargo test --workspace`
- `cargo deny check licenses` (configured via `deny.toml`)
- `ruff check python/` (Python quality)

## Branch Discipline
- Feature work: `<repo>-wtrees/<subject>/` (e.g., `AgilePlus-wtrees/<topic>/`)
- Canonical `AgilePlus/` = bare repo (main only, no direct commits)
- Tracked workspace: `agileplus/` (lowercase; actual git worktree)
- Branch naming: `chore/`, `feat/`, `fix/` prefixes

## Governance Integration
- Specs: `kitty-specs/<feature-id>/` (relative to agileplus workspace root)
- Worklog: `AgilePlus/.work-audit/worklog.md`

## Repo Structure
- `agileplus/` — **primary tracked workspace** (lowercase; all actual source lives here)
- `AgilePlus/` — bare git repo (remote: <REDACTED>/AgilePlus; commits only via PR merge)
- `*-wtrees/` — feature worktrees; safe to work in directly
- `kitty-specs/` — root-level spec archive (legacy, read-only)
- Individual repos: `Agentora/`, `pheno/`, etc.

## Important Notes
- **Never commit directly to `AgilePlus/` main** — it is bare. All changes go through PRs.
- **Do not use `AgilePlus-wtrees/<subject>/`** — the worktree convention is `<repo>-wtrees/` (lowercase repo name).
- See `agileplus/CLAUDE.md` for detailed workspace structure, bootstrap status, and agent operating notes.

## Architecture Decision Records

This repo documents architecture decisions in two locations:
- **`ADR.md`** (root) --- inline ADR-001 through ADR-014
- **`docs/adr/`** --- individual ADR files covering additional decisions

| ID | Title | Status | Location |
|----|-------|--------|----------|
| ADR-001 | Rust Workspace Monorepo with 22 Crates | Accepted | [`ADR.md`](ADR.md) |
| ADR-002 | Hexagonal Architecture with Port/Adapter Pattern | Accepted | [`ADR.md`](ADR.md) |
| ADR-003 | SQLite as Local-First Storage with Optional External Sync | Accepted | [`ADR.md`](ADR.md) |
| ADR-004 | SHA-256 Hash-Chained Immutable Audit Log and Event Store | Accepted | [`ADR.md`](ADR.md) |
| ADR-005 | gRPC Service Layer with Tonic + Protobuf | Accepted | [`ADR.md`](ADR.md) |
| ADR-006 | NATS JetStream as the Event Bus | Accepted | [`ADR.md`](ADR.md) |
| ADR-007 | Plugin Architecture via External Git-Sourced Crates | Accepted | [`ADR.md`](ADR.md) |
| ADR-008 | Python MCP Server for AI Agent Integration | Accepted | [`ADR.md`](ADR.md) |
| ADR-009 | OpenTelemetry for Observability with OTLP Export | Accepted | [`ADR.md`](ADR.md) |
| ADR-010 | process-compose for Local Dev Orchestration | Accepted | [`ADR.md`](ADR.md) |
| ADR-011 | Credentials Management via OS Keychain | Accepted | [`ADR.md`](ADR.md) |
| ADR-012 | P2P Replication with Vector Clocks | Accepted | [`ADR.md`](ADR.md) |
| ADR-013 | Neo4j for Graph-Based Dependency Queries | Accepted | [`ADR.md`](ADR.md) |
| ADR-014 | Import Subsystem with Manifest-Driven Ingestion | Accepted | [`ADR.md`](ADR.md) |
| ADR-0002 | Integration/Consolidate Branch Strategy | Accepted | [`docs/adr/0002-integration-consolidate-branch-strategy.md`](docs/adr/0002-integration-consolidate-branch-strategy.md) |
| ADR-0003 | Docs Tree Consolidation | Accepted | [`docs/adr/0003-docs-tree-consolidation.md`](docs/adr/0003-docs-tree-consolidation.md) |
| ADR-0004 | JSON Metadata to YAML Frontmatter + Code Decorators | Accepted | [`docs/adr/0004-json-to-frontmatter-decorators.md`](docs/adr/0004-json-to-frontmatter-decorators.md) |
| ADR-0005 | traceability-core Git Dependency | Accepted | [`docs/adr/0005-traceability-core-git-dependency.md`](docs/adr/0005-traceability-core-git-dependency.md) |
| ADR-0006 | Absorb agileplus-spec-harmonizer into workspace | Accepted | [`docs/adr/0006-agileplus-spec-harmonizer-absorption.md`](docs/adr/0006-agileplus-spec-harmonizer-absorption.md) |
| --- | Task Runner Selection | Accepted | [`docs/adr/001-task-runner-selection.md`](docs/adr/001-task-runner-selection.md) |
| --- | Registry Adapter Architecture | Accepted | [`docs/adr/002-registry-adapter-architecture.md`](docs/adr/002-registry-adapter-architecture.md) |
| ADR-012 | Plugin Architecture (docs/adr copy) | Accepted | [`docs/adr/ADR-012-plugin-architecture.md`](docs/adr/ADR-012-plugin-architecture.md) |
