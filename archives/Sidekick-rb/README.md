> Work state: docs polish in progress | Progress: ██████░░░░ 6/10

Sidekick is a Phenotype workspace for agent-facing utilities, including presence/status tracking, low-cost LLM routing, and messaging adapters. It is a multi-language collection with independently versioned crates and a focus on reusable infrastructure for agent workflows.

## Usage / Quickstart

```bash
cd /Users/kooshapari/CodeProjects/Phenotype/repos/Sidekick
cargo build --release --workspace
cargo test --workspace
```

<!-- AI-DD-META:START -->
<!-- This repository is planned, maintained, and managed by AI Agents only. -->
<!-- Slop issues are expected and intentionally present as part of an HITL-less -->
<!-- /minimized AI-DD metaproject of learning, refining, and building brute-force -->
<!-- training for both agents and the human operator. -->
![Downloads](https://img.shields.io/github/downloads/KooshaPari/Sidekick/total?style=flat-square&label=downloads&color=blue) [![AI slop inside](https://sladge.net/badge.svg)](https://sladge.net)
![GitHub release](https://img.shields.io/github/v/release/KooshaPari/Sidekick?style=flat-square&label=release)
![License](https://img.shields.io/github/license/KooshaPari/Sidekick?style=flat-square)
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
> **Pinned references (Phenotype-org)**
> - MSRV: see rust-toolchain.toml
> - cargo-deny config: see deny.toml
> - cargo-audit: rustsec/audit-check@v2 weekly
> - Branch protection: 1 reviewer required, no force-push
> - Authority: phenotype-org-governance/SUPERSEDED.md

# Sidekick — Agent Utility Collection

![Sidekick Logo](assets/logo-placeholder.svg)

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/rust-1.83+-orange.svg?logo=rust&logoColor=white)](Cargo.toml)
[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](#)

**Sidekick collection** — Agent micro-utilities for Phenotype org. 3 canonical members, all at gold-standard FR coverage.

A named Rust workspace consolidating core agent infrastructure utilities for the Phenotype ecosystem.

## Members

| Name | Repository | Status | FR Prefix | FR Coverage | Purpose |
|------|-----------|--------|-----------|-------------|---------|
| **agent-user-status** | [agent-user-status](../agent-user-status) | CANONICAL | FR-USR | 67/67 | User presence & status tracking (MCP server) |
| **cheap-llm-mcp** | [cheap-llm-mcp](../cheap-llm-mcp) | CANONICAL | FR-LLM | 38/38 | Budget LLM routing (FastMCP + Python) |
| **sidekick-messaging** | [Sidekick/crates/sidekick-messaging](./crates/sidekick-messaging) | CANONICAL | FR-MSG | Pending | iMessage/SMS messaging bridge adapter (Rust stub) |

### Rejected Candidates

| Name | Reason | Audit |
|------|--------|-------|
| **PhenoAgent** | <1% test coverage, 0 adopters | [W-68D audit](../phenotype-org-audits/audits/2026-04-24/collection_build_matrix.md) |
| **phenotype-skills** | Empty stub, not ready for adoption | [W-68D audit](../phenotype-org-audits/audits/2026-04-24/collection_build_matrix.md) |

## Quality Bar

**Sidekick canonical standard:** All canonical members maintain 100% functional requirement traceability.

- **agent-user-status**: 67 FRs, 100% traced to tests
- **cheap-llm-mcp**: 38 FRs, 100% traced to tests
- **sidekick-messaging**: FR scaffolding pending integration

See [docs/FUNCTIONAL_REQUIREMENTS.md](docs/FUNCTIONAL_REQUIREMENTS.md) for the current
functional requirement inventory.

## Quick Start

```bash
cd /Users/kooshapari/CodeProjects/Phenotype/repos/Sidekick
cargo build --release
cargo test --workspace
```

## Integration Map

- **agent-user-status** — MCP tools: `user_status`, `record_presence_signal`, `set_user_status`, eye-tracking, presence signals
- **cheap-llm-mcp** — Skill routing for low-cost LLM completions (Minimax, Kimi, Fireworks)
- **sidekick-messaging** — Unified messaging adapter (stub); wraps iMessage, SMS, email via agent-imessage skill
- **PhenoAgent** — Foundational agent framework; integrates cheap-llm-mcp + agent-user-status + sidekick-messaging
- **phenotype-skills** — Shared skill definitions consumed by PhenoAgent and external agents

## Architecture

Sidekick is a polyglot workspace:
- **Rust crates** (`crates/sidekick-*`): Compiled binaries and libraries
- **Python sub-package** (`crates/sidekick-cheap-llm`): FastMCP wrapper, imported as Python module

Each sub-crate is independently versioned and consumable; consumers import only what they need.

## Release Registry

See `release-registry.toml` for version metadata, stability information, and sub-crate status. The master index of all Phenotype collections is at `../phenotype-collections.toml`.

Schema documentation: `docs/governance/release_registry_schema.md`

## Cross-Collection Integration

Sidekick is part of the **Phenotype named collections**:

- **Sidekick** (this) — Agent dispatch & presence
- **Eidolon** — Device automation (desktop, mobile, sandbox)
- **Observably** — Distributed tracing & observability
- **Stashly** — State, events, caching, migrations
- **Paginary** — Knowledge collection (specs, tutorials, handbooks)

### Event Bus

Sidekick uses **phenoEvents** for cross-collection communication. The historical `phenotype-bus` repository is archived; event-bus work was migrated to `KooshaPari/phenoEvents`. Collections emit domain events that other collections consume without hardcoded dependencies:

```rust
use phenotype_bus::{Bus, Event};
use serde::Serialize;

#[derive(Clone, Serialize)]
pub struct DispatchStarted {
    pub provider: String,
}

impl Event for DispatchStarted {
    fn event_name(&self) -> &'static str { "DispatchStarted" }
}

// Emit event
let bus = Bus::new(100);
bus.publish(DispatchStarted { provider: "forge".into() }).await?;

// Subscribe in another collection (e.g., Eidolon)
let mut rx = bus.subscribe();
while let Ok(event) = rx.recv().await {
    println!("Got dispatch event: {}", event.event_name());
}
```

See [phenoEvents](../phenoEvents/README.md) and the
[collection build matrix](../phenotype-org-audits/audits/2026-04-24/collection_build_matrix.md)
for integration details.

## Publishing

Crates published to crates.io under `sidekick-*` prefix.

## See Also

Explore Sidekick and other Phenotype collections at the [Collections Showcase](https://dev.phenotype.io/collections).

**Sibling Collections:**
- **[Eidolon](../Eidolon)** — Unified trait-based device automation (desktop, mobile, sandbox)
- **[Stashly](../Stashly)** — Storage & persistence (caching, event sourcing, state machines)
- **[Observably](../PhenoObservability)** — Observability & distributed tracing
- **[Paginary](../Paginary)** — Knowledge collection (specs, tutorials, handbooks)
- **[phenotype-shared](../phenoShared)** — Rust infrastructure toolkit (domain, application, ports)

## Development & Governance

**AgilePlus Tracking**: All work tracked in `/repos/AgilePlus`. Review `CLAUDE.md` for development contracts and policies.

**Quality Gates**:
```bash
cargo build --release --workspace      # Full release build
cargo test --workspace                 # Complete test suite
cargo clippy --workspace -- -D warnings # Zero warnings required
cargo fmt --check                      # Format validation
```

**Crate Publishing**: Each sub-crate published independently to crates.io with `sidekick-*` prefix. Version metadata in root `Cargo.toml`.

**Cross-Collection Integration**: Sidekick integrates with phenoEvents for async event streaming; phenotype-bus is archived historical context only. Other collections (Stashly, Observably, Eidolon) consume dispatch events for specialized handling.

## Related Phenotype Collections

- **[Eidolon](../Eidolon)** — Device automation & virtualization
- **[Observably](../PhenoObservability)** — Distributed tracing & observability
- **[Stashly](../Stashly)** — State, events, caching, persistence
- **[Paginary](../Paginary)** — Knowledge collection
- **[phenotype-shared](../phenoShared)** — Shared infrastructure

## License

MIT — see [LICENSE](./LICENSE).

**Status**: Active development (Phase 2 in progress)  
**Collections Showcase**: https://dev.phenotype.io/collections  
**Last Updated**: 2026-04-24

## Documentation

This repository includes the following cross-cutting documents:

- [`AGENTS.md`](AGENTS.md) — operating instructions for AI agents and human contributors
- [`docs/`](docs/) — design notes, ADRs, and supporting documentation (see [`docs/index.md`](docs/index.md))
