# AGENTS.md — pheno

Phenotype Shared Crates (Rust) — Agent Rules

## Quick Links

- **Local CLAUDE.md:** See `CLAUDE.md` in this repository for project-specific guidance
- **Phenotype org governance:** `/Users/kooshapari/CodeProjects/Phenotype/repos/CLAUDE.md`
- **Global agent guidance:** `~/.claude/AGENTS.md`
- **AgilePlus work tracking:** `cd /Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus && agileplus <command>`

## CI/CD Status

**GitHub Actions billing exhausted** (as of 2026-09-15). All workflow runs fail at 0s with billing errors. This is a permanent constraint (repo does not pay for GH Actions).

**What works:**
- 23 workflows are structurally correct and documented in `.github/workflows/`
- Local verification via `just grade` (lint + test + audit + unused deps)
- Local release via `bash scripts/release.sh v0.2.0`

**What doesn't:**
- No GitHub-hosted runners available (free tier exhausted)
- Workflow runs cancel immediately
- Dependabot PRs cannot auto-merge

**Workaround:** Use `scripts/release.sh` for local release builds. When runners become available, the full CI pipeline will work as-is.

## Key Workflows

1. **Before implementing:** Check AgilePlus for existing specs (`agileplus status`)
2. **Quality gates:** Run linters, tests, and docs validation locally:
   - `cargo test --workspace`
   - `cargo clippy --workspace -- -D warnings`
   - `cargo fmt --check`
3. **Worktrees:** Use `.worktrees/<topic>/` for feature work (e.g., `.worktrees/feature-xyz/`)
4. **Integration:** Commit to canonical repo (`main`) after quality gates pass
5. **Cargo build/check:** Do NOT run cargo build/check in multi-agent sessions (hangs on 70-crate workspace)

## Project-Specific Gotchas

### Build & Testing
- No `cargo build` or `cargo check` in shared sessions (will hang)
- Only `cargo test`, `cargo clippy`, and `cargo fmt` are safe
- See CLAUDE.md for language stack, build commands, and testing requirements

### Workspace Members
- Each crate in `crates/` is independent; check `Cargo.toml` members before adding
- Comment out missing crates with `# missing-as-of-YYYY-MM-DD` rather than removing

### FR Traceability
- All tests MUST reference FR IDs in comments: `// Traces to: FR-XXX-NNN`
- Verify via: `grep -r "Traces to:" crates/*/src/**/*.rs`

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
| ADR-015 | Phenotype Crate Organization & PR Guidelines | Proposed | [`docs/adr/ADR-015-crate-organization.md`](docs/adr/ADR-015-crate-organization.md) |
| --- | Task Runner Selection | Accepted | [`docs/adr/001-task-runner-selection.md`](docs/adr/001-task-runner-selection.md) |
| --- | Registry Adapter Architecture | Accepted | [`docs/adr/002-registry-adapter-architecture.md`](docs/adr/002-registry-adapter-architecture.md) |
| --- | Architecture Overview | --- | [`docs/adr/ARCHITECTURE.md`](docs/adr/ARCHITECTURE.md) |

---

**Parent contract:** Extends Phenotype-org governance. See `CLAUDE.md` and parent `AGENTS.md` for complete operating procedures.
