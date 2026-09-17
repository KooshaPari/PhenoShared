# PhenoShared

**Phenotype shared workspace — the main monorepo coordinating the Phenotype ecosystem across Rust, Swift, TypeScript, and Python.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Rust](https://img.shields.io/badge/rust-1.81%2B-orange.svg)](https://www.rust-lang.org/)
[![Workspace: Cargo](https://img.shields.io/badge/workspace-cargo-blueviolet.svg)](https://doc.rust-lang.org/cargo/)
[![Crates: 365+](https://img.shields.io/badge/crates-365%2B-success.svg)](./crates/)

---

## What is this?

`phenoAI` is the **shared Phenotype workspace** at `KooshaPari/PhenoShared`. It hosts **365+ crates**, several standalone apps, and the documentation/contracts that bind the Phenotype ecosystem together. It is *not* a single product — it is the substrate, engines, fabric, integrations, tooling, and apps that specialized products (PhenoMLX, HeliosLab, Portage, …) are built on top of.

Distinct from PhenoMLX, which focuses on MLX-native multi-backend inference, this repository owns:

- the **Rust core** (substrate, engines, fabric, agileplus, phenotype-*, store-*, wave, supervisor, …)
- the **agent dispatch surface** (Claude / Codex / Forge / A2A / AgentAPI engines, OmniRoute adapters, cloud bridges)
- the **client applications** (phinbox-app, bench-cockpit, byteport, tooling, desktop shells)
- the **contracts and docs** that keep all of the above consistent (ARCHITECTURE.md, ADR/, docs/, AGENTS.md)

If a change extends Fabric into governed-intent, agent dispatch, economic allocation, evidence-graph, session-ledger, or process-supervision domains, an ADR is required first (see `CONTRIBUTING.md`).

## Highlights

- **Polyglot by default, Rust-first where it wins.** No language is forbidden; the choice is driven by measured performance and fit.
- **Capability-based runtime.** Substrate layer exposes typed ports and adapters; engines compose on top.
- **Multi-agent orchestration.** `engine-claude`, `engine-codex`, `engine-forge`, `engine-a2a`, `engine-agentapi` and the `agileplus-*` intent plane.
- **Fabric layer.** Distributed topology, capability inventory, route plans, leases, and surface isolation (absorbed 2026-09-16).
- **Production-grade quality gates.** Workspace `cargo clippy --workspace -- -D warnings`, `unsafe_code = "forbid"`, and dedicated CI.

## Key Crates (Sampled)

The workspace contains **365+ crates**; this is a representative sample, grouped by family. Package names match each crate's `Cargo.toml` `[package].name`.

### Substrate (core runtime)

| Crate | Package | Purpose |
|-------|---------|---------|
| `crates/substrate` | `substrate` | Rust SDK facade: hexagonal ports, domain types, dispatch planner, optional adapters |
| `crates/substrate-core` | `substrate-core` | Inner core types and traits |
| `crates/substrate-app` | `substrate-app` | Application runtime on top of substrate-core |
| `crates/substrate-trace` | `substrate-trace` | Distributed tracing primitives |
| `crates/substrate-schedule` | `substrate-schedule` | Scheduling primitives |
| `crates/substrate-dag` | `substrate-dag` | Workflow DAG execution |
| `crates/substrate-skills` | `substrate-skills` | Skill system for agents |
| `crates/substrate-memory` | `substrate-memory` | Agent memory layer |
| `crates/substrate-serve-lock` | `substrate-serve-lock` | Worktree locking mechanism |
| `crates/substrate-tui` | `substrate-tui` | Terminal UI primitives |

### Engines (agent execution)

| Crate | Package | Purpose |
|-------|---------|---------|
| `crates/engine-spec` | `engine-spec` | Engine contract and conformance specification |
| `crates/engine-forge` | `engine-forge` | Plugin execution engine |
| `crates/engine-claude` | `engine-claude` | Claude agent integration |
| `crates/engine-codex` | `engine-codex` | Codex agent integration |
| `crates/engine-a2a` | `engine-a2a` | Agent-to-agent communication |
| `crates/engine-agentapi` | `engine-agentapi` | Generic agent API integration |
| `crates/engine-conformance` | `engine-conformance` | Engine conformance test suite |

### AgilePlus (intent / planning)

| Crate | Package | Purpose |
|-------|---------|---------|
| `crates/agileplus-api` | `agileplus-api` | Public API surface |
| `crates/agileplus-cli` | `agileplus-cli` | Command-line interface |
| `crates/agileplus-domain` | `agileplus-domain` | Domain types |
| `crates/agileplus-events` | `agileplus-events` | Event sourcing |
| `crates/agileplus-graph` | `agileplus-graph` | Intent graph |
| `crates/agileplus-git` | `agileplus-git` | Git-backed intent store |
| `crates/agileplus-github` | `agileplus-github` | GitHub adapter |
| `crates/agileplus-nats` | `agileplus-nats` | NATS event bus |
| `crates/agileplus-sqlite` | `agileplus-sqlite` | SQLite store |
| `crates/agileplus-cache` | `agileplus-cache` | Cache layer |
| `crates/agileplus-telemetry` | `agileplus-telemetry` | Telemetry hooks |
| `crates/agileplus-triage` | `agileplus-triage` | Triage workflows |

### Phenotype (core integrations)

| Crate | Package | Purpose |
|-------|---------|---------|
| `crates/phenotype-cli` | `phenotype-cli` | Phenotype command-line |
| `crates/phenotype-mcp` | `phenotype-mcp` | MCP server infrastructure |
| `crates/phenotype-hub` | `phenotype-hub` | Hub/orchestration facade |
| `crates/phenotype-core` | `phenotype-core` | Shared core types |
| `crates/phenotype-contracts` | `phenotype-contracts` | Cross-crate contracts |
| `crates/phenotype-shared` | `phenotype-shared` | Shared utilities |
| `crates/phenotype-config` | `phenotype-config` | Configuration types and loader |
| `crates/phenotype-event-bus` | `phenotype-event-bus` | Event bus |
| `crates/phenotype-policy-engine` | `phenotype-policy-engine` | Policy engine |
| `crates/phenotype-routing` | `phenotype-router` | Routing helpers |

### Fabric (distributed fabric layer)

| Crate | Package | Purpose |
|-------|---------|---------|
| `crates/fabric-capability` | `fabric-capability` | Capability inventory |
| `crates/fabric-capability-ffi` | `fabric-capability-ffi` | C ABI for capability layer |
| `crates/fabric-graph` | `fabric-graph` | Topology and routing graph |
| `crates/fabric-checker` | `fabric-checker` | Capability/lease checks |
| `crates/fabric-cli` | `fabric-cli` | Fabric CLI |
| `crates/fabric-gui` | `fabric-gui` | GUI shell (Tauri) |
| `crates/fabric-daemon` | `fabric-daemon` | Long-running fabric daemon |
| `crates/fabric-frame-transport` | `fabric-frame-transport` | Frame-based transport |
| `crates/fabric-surface-mojo` | `fabric-surface-mojo` | Mojo surface adapter |

### Storage, transport, drivers

| Crate | Package | Purpose |
|-------|---------|---------|
| `crates/store-file` | `store-file` | File-based storage |
| `crates/store-sqlite` | `store-sqlite` | SQLite storage |
| `crates/transport-file` | `transport-file` | File transport |
| `crates/runtime-process` | `runtime-process` | Process isolation and sandboxing |
| `crates/supervisor` | `supervisor` | Process supervision tree |
| `crates/file-watcher` | `file-watcher` | Cross-platform file watching |
| `crates/wave` | `wave` | 3-lane reliability protocol |
| `crates/wave-3lane-tests` | `wave-3lane-tests` | Wave conformance suite |
| `crates/driver-cli` | `driver-cli` | CLI driver |
| `crates/driver-http` | `driver-http` | HTTP driver |
| `crates/driver-argv` | `driver-argv` | Argv driver |
| `crates/driver-mcp` | `driver-mcp` | MCP driver |

### Integrations and adapters

| Crate | Package | Purpose |
|-------|---------|---------|
| `crates/omniroute-adapter` | `omniroute-adapter` | OmniRoute integration adapter |
| `crates/dispatch-bridge` | `dispatch-bridge` | Cross-engine dispatch bridge |
| `crates/cliproxy-adapter` | `cliproxy-adapter` | CLI proxy adapter |
| `crates/context-budget` | `context-budget` | Token/context budget management |
| `crates/cloud-codex` | `cloud-codex` | Codex cloud integration |
| `crates/cloud-cursor` | `cloud-cursor` | Cursor cloud integration |
| `crates/cloud-kilo` | `cloud-kilo` | Kilo cloud integration |
| `crates/cloud-dispatch-conformance` | `cloud-dispatch-conformance` | Cloud dispatch conformance |
| `crates/a2a` | `a2a` | Agent-to-agent primitives |
| `crates/cli-wrapper` | `playcua-cli-wrapper` | CLI wrapper (PlayCUA) |

## Repository Structure

```
phenoAI/
├── apps/                  # User-facing applications (mixed languages)
│   ├── bench-cockpit/     # Bun + TypeScript benchmark cockpit
│   ├── byteport/          # Data transfer utility
│   ├── desktop/           # Desktop shell resources (macOS)
│   ├── phinbox-app/       # Phinbox notification app (Swift)
│   └── tooling/           # Tauri-based developer tooling
│
├── crates/                # 365+ Rust crates (workspace members)
│   ├── substrate*/        # Core runtime substrate
│   ├── engine-*/          # Agent execution engines
│   ├── agileplus-*/       # Intent and planning system
│   ├── phenotype-*/       # Core integrations and shared types
│   ├── fabric-*/          # Distributed fabric layer
│   ├── store-*/           # Storage backends
│   ├── driver-*/          # Driver surfaces (cli/http/argv/mcp)
│   ├── cloud-*/           # Cloud integrations
│   └── ...                # ~300 more domain crates
│
├── tools/                 # Standalone tooling executables (workspace members)
│   ├── fake-forge/        # Forge agent simulator
│   ├── fake-codex-cloud/  # Codex cloud simulator
│   ├── iac-plan-viewer/   # Infrastructure-as-code visualizer
│   ├── org-audits/        # Organizational audit tooling
│   └── check-ecosystem.ts # Ecosystem linting entrypoint
│
├── docs/                  # Documentation
│   ├── architecture/      # Architecture overviews (overview, ports, domain-model)
│   ├── adr/               # Architecture Decision Records (0001-…)
│   ├── api/               # API reference
│   ├── guides/            # User and developer guides
│   ├── contributing/      # Contributing playbooks
│   └── atlas/             # Cross-repo atlas and assessments
│
├── scripts/               # Workspace utility scripts (CI helpers, harnesses)
├── configs/               # Configuration templates
├── benches/               # Performance benchmarks
│
├── ARCHITECTURE.md        # Top-level architecture (read first)
├── CONTRIBUTING.md        # Contribution rules (read first)
├── AGENTS.md              # Agent contract (worktree, language policy)
├── CLAUDE.md              # Claude-specific guide
├── CHARTER.md             # Project charter
├── ADR.md / ADRS.md       # ADR index
├── Cargo.toml             # Workspace manifest (365+ members)
└── Cargo.lock             # Workspace lockfile
```

## Quick Start

### Prerequisites

- **Rust** 1.81+ via [rustup](https://rustup.rs/) (workspace lints are pinned in `Cargo.toml`'s `[workspace.lints.rust]` and `[workspace.package]`)
- **Git** 2.0+
- Optional:
  - `cargo-deny` — `cargo install cargo-deny`
  - `mdBook` — `cargo install mdbook` (for `docs/book.toml`)
  - **Bun** (for `apps/bench-cockpit`)
  - **Xcode / Swift toolchain** (for `apps/phinbox-app`)
  - **Tauri prerequisites** (for `apps/tooling`, `crates/fabric-gui`)

### Clone and build

```bash
git clone https://github.com/KooshaPari/PhenoShared.git
cd PhenoShared

# Build the workspace (may take a while on a cold cache)
cargo build --workspace

# Run the test suite
cargo test --workspace

# Lint (CI policy: deny warnings)
cargo clippy --workspace -- -D warnings

# Format
cargo fmt --all

# Generate crate docs locally
cargo doc --workspace --no-deps --open
```

### Run a representative subset

```bash
# Phenotype command-line
cargo run -p phenotype-cli -- --help

# AgilePlus CLI
cargo run -p agileplus-cli -- --help

# Phenotype MCP server
cargo run -p phenotype-mcp -- --help

# Fabric CLI
cargo run -p fabric-cli -- --help

# Substrate binary
cargo run -p substrate -- --help
```

> **Tip:** the workspace excludes `crates/forge_daemon`, `crates/fabric-frame-transport/fuzz`, and `crates/fabric-gui/src-tauri` from the default members (see `[workspace] exclude` in `Cargo.toml`). Pass `--workspace` to include them explicitly when needed.

## Architecture

Start with **[ARCHITECTURE.md](./ARCHITECTURE.md)** for the high-level picture, then read:

- [`docs/architecture/overview.md`](./docs/architecture/overview.md) — system overview
- [`docs/architecture/domain-model.md`](./docs/architecture/domain-model.md) — domain model
- [`docs/architecture/ports.md`](./docs/architecture/ports.md) — hexagonal ports & adapters
- [`docs/architecture/development-container.md`](./docs/architecture/development-container.md) — dev environment
- [`docs/architecture/rust-analyzer.md`](./docs/architecture/rust-analyzer.md) — IDE wiring

For decisions and trade-offs, browse **[`docs/adr/`](./docs/adr/)** (e.g. `0001-record-architecture-decisions.md`, `0002-hexagonal-ports-adapters.md`, `0003-universal-typed-graph.md`).

Layered architecture (top → bottom):

1. **Applications** — `apps/` (phinbox-app, bench-cockpit, byteport, tooling, desktop)
2. **Adapters / drivers** — `crates/driver-*`, MCP surfaces, CLI wrappers
3. **Engines** — `crates/engine-*` (claude, codex, forge, a2a, agentapi, conformance)
4. **AgilePlus** — intent / planning / events (`crates/agileplus-*`)
5. **Substrate** — hexagonal ports, dispatch planner, tracing, DAG, skills, memory
6. **Fabric** — distributed topology, capabilities, leases, transport
7. **Storage** — `crates/store-file`, `crates/store-sqlite`

## Workspace Conventions

- **Edition:** Rust 2021 (see `[workspace.package] edition`)
- **Safety:** `unsafe_code = "forbid"` is the default
- **Lint policy:** `[workspace.lints.rust]` is the source of truth; CI runs `cargo clippy --workspace -- -D warnings`
- **Members:** declared in `Cargo.toml` `members = [ … ]`; exclusions are explicit
- **Commits:** every agent commit carries `tx-agent:` and `tx-validated:` trailers (immutable transaction ledger — see `AGENTS.md` §"Immutable Transaction Ledger")
- **Worktrees:** feature work happens in `repos/worktrees/phenoAI/<topic>` (see `AGENTS.md`)
- **ADR-first:** any change that extends this repo into governed intent, agent dispatch, economic allocation, evidence graph, session ledger, or process supervision requires an ADR before code

## Contributing

1. Read **[`CONTRIBUTING.md`](./CONTRIBUTING.md)** and **[`AGENTS.md`](./AGENTS.md)** in full.
2. Read **[`CHARTER.md`](./CHARTER.md)** and the relevant ADR in **[`docs/adr/`](./docs/adr/)**.
3. Fork or use a worktree:
   ```bash
   git -C ~/CodeProjects/Phenotype/repos/phenoAI \
       worktree add ../worktrees/phenoAI/<topic> -b <topic>
   ```
4. Make changes; run `cargo fmt`, `cargo clippy --workspace -- -D warnings`, and `cargo test --workspace`.
5. Commit with the ledger trailers (see `~/.gitmessage` template).
6. Open a PR referencing the relevant ADR / issue.

Bug reports and security disclosures: see `CODE_OF_CONDUCT.md` and `SECURITY.md`.

## Related Repositories

| Repository | Role |
|---|---|
| **[KooshaPari/PhenoShared](https://github.com/KooshaPari/PhenoShared)** | This workspace (main monorepo) |
| **[KooshaPari/phenotype-omlx](https://github.com/KooshaPari/phenotype-omlx)** | PhenoMLX — MLX-native inference stack built on top of Phenotype engines |
| **[KooshaPari/HeliosLab](https://github.com/KooshaPari/HeliosLab)** | Experimental hardware-integration lab |
| **[KooshaPari/portage](https://github.com/KooshaPari/portage)** | Deployment and release engineering |

## License

Dual-licensed under your choice of:

- **[MIT](./LICENSE-MIT)**
- **[Apache 2.0](./LICENSE-APACHE)**

Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion is licensed under the same terms.

## Acknowledgements

Built by the Phenotype open-source community. Special thanks to all contributors who have helped shape this workspace.

---

*Last refreshed: September 2026. For canonical product state, see [`docs/atlas/`](./docs/atlas/) and [`docs/architecture/overview.md`](./docs/architecture/overview.md).*
