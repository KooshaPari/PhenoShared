# Architecture

## System Overview

`CodeProjects/Phenotype/repos` is a **polyrepo shelf**: a single directory containing independent Git repositories that together form the Phenotype engineering portfolio. It is not a single deployable application and not a conventional monorepo; each project owns its own code, tests, CI, releases, and README.

The shelf groups four kinds of systems:

- **Product repos**: CLIs, MCP services, dashboards, web apps, and local workflow tools.
- **Shared foundations**: reusable Rust crates and language-specific support packages used across products.
- **Agent automation**: MCP servers, model gateways, status services, and workflow agents.
- **Governance and release infrastructure**: specs, ADRs, worklogs, CI templates, security scans, and org-wide release automation.

AgilePlus is the work-tracking spine for this shelf: work is described as specs and work packages, implemented in repo-specific worktrees, then merged back to the owning canonical repo.

## Component Ownership

### Work tracking: AgilePlus

| Component | Location | Ownership |
|-----------|----------|-----------|
| AgilePlus product | `AgilePlus/` | Local-first, spec-driven project-management CLI and service workspace. |
| Core Rust crates | `AgilePlus/crates/agileplus-*` | Domain model, CLI, API, gRPC, SQLite, Git/GitHub sync, events, telemetry, p2p, dashboard, import, triage, and tests. |
| Live specs | `AgilePlus/kitty-specs/` and shelf `kitty-specs/` | Feature specs, work packages, and acceptance criteria. |
| OpenAPI surface | `AgilePlus/openapi.yaml` | REST contract for feature, work-package, event, audit, and governance APIs. |
| MCP bridge | `agileplus-mcp/` | Python FastMCP bridge from LLM tools to the AgilePlus gRPC/API surface. |
| Agent helpers | `agileplus-agents/` | Rust helpers for agent orchestration and workspace automation. |
| Landing site | `agileplus-landing/` | Public/marketing web surface. |

### Shared foundations

| Component | Location | Ownership |
|-----------|----------|-----------|
| Shared Rust toolkit | `phenoShared/` | Cross-project Rust crates for common infrastructure and reusable contracts. |
| Infrastructure crates | `phenotype-infrakit/` | Shared error, health, config, metrics, tracing, hexagonal architecture, plugin, and utility crates. |
| Shelf-level Rust placeholders | `crates/` | AgilePlus/shelf-local shared crates that have not yet moved into a named repo. |
| Protocol definitions | `proto/`, `buf.yaml`, `buf.gen.yaml` | Protobuf/gRPC contracts shared by Rust, Go, Python, and MCP layers. |

Shared behavior should move into `phenoShared` or `phenotype-infrakit` before it is duplicated across product repos.

### Product and application surfaces

| Component | Location | Ownership |
|-----------|----------|-----------|
| Org CLI | `pheno-cli/` | Go CLI for org-wide release governance and workflow automation. |
| Federated app workspace | `pheno/` | Multi-product Rust workspace for app/platform surfaces such as Logify, Metron, Tasken, Stashly, Settly, and Authvault. |
| Dotfiles/environment manager | `thegent/` | Rust/Python agent-oriented task runner and developer environment manager. |
| Helios app manager | `helios-cli/`, `heliosApp/`, `HeliosLab/` | Helios CLI/app surfaces and lab tooling. |
| Agent API gateway | `agentapi-plusplus/` | HTTP/WebSocket API surface for agent integrations. |
| CLI proxy API | `cliproxyapi-plusplus/` | Authenticated CLI proxy/API service. |
| Data and platform projects | `DataKit/`, `FocalPoint/`, `PolicyStack/`, `BytePort/`, `Configra/`, `Conft/`, `hwLedger/`, `phenoAI/` | Product-specific data, policy, platform, file/artifact, config, hardware-ledger, and AI integration surfaces. |

### Agent automation

| Component | Location | Ownership |
|-----------|----------|-----------|
| MCP integration hub | `AgentMCP/`, `PhenoMCP/` | MCP-facing integration surfaces. |
| Cheap model gateway | `cheap-llm-mcp/` | Python FastMCP gateway for Kimi/Minimax/Codex-style bulk reasoning. |
| Agent status | `agent-user-status/` | Presence/status signalling for local agents. |
| Agent experiments | `Agentora/`, `bare-cua/`, `agent-devops-setups/`, `agentops-policy-federation/` | Agent orchestration, computer-use, devops setup, and policy federation experiments. |

### Docs, governance, and release infrastructure

| Component | Location | Ownership |
|-----------|----------|-----------|
| Cross-project docs | `docs/` | Engineering standards, governance, and reference material. |
| Worklogs | `worklogs/` | Architecture, governance, duplication, dependency, performance, integration, and research decisions. |
| Specs | `kitty-specs/` | Shelf-level AgilePlus specs and stabilization work packages. |
| CI templates | `.github/workflows/` and per-repo `.github/workflows/` | Security, quality, release, SBOM, and documentation checks. |
| Web landings | `*-landing/`, `projects-landing/`, `phenokits-landing/` | Independently deployed marketing and portfolio sites. |

## Runtime Data Flow

### AgilePlus runtime

```text
User or agent
  -> agileplus CLI / dashboard / REST / gRPC / MCP tool
  -> agileplus-domain and agileplus-subcmds
  -> adapters: agileplus-sqlite, agileplus-git, agileplus-github, agileplus-nats, agileplus-p2p
  -> persisted specs, SQLite state, Git worktrees, GitHub Issues, NATS events, or peer sync
  -> telemetry through agileplus-telemetry and OTEL exporters
```

`agileplus-mcp` lets LLM agents call AgilePlus workflows without shelling into the CLI directly: the MCP service validates tool input, bridges to the Rust service/API layer, and returns structured tool results.

### Cross-repo product runtime

```text
User / automation / agent
  -> product surface (CLI, MCP server, web app, API, or dashboard)
  -> repo-local orchestration layer
  -> shared crates/packages from phenoShared or phenotype-infrakit
  -> adapters for GitHub, filesystem, SQLite/Postgres/Redis, LLM providers, or deployment targets
  -> traces/logs/events emitted through repo-local telemetry conventions
```

Examples:

- `pheno-cli` drives org-wide governance, release, and audit operations across repositories.
- `cheap-llm-mcp` brokers agent requests to lower-cost model providers and returns MCP tool results.
- `agentapi-plusplus` and `cliproxyapi-plusplus` expose service/API boundaries for agent and CLI workflows.
- Product repos consume shared Rust infrastructure rather than copying error/config/health/telemetry logic.

## Release Flow

1. **Specify**: work starts in the relevant AgilePlus spec under `kitty-specs/` or the owning repo's `AgilePlus/kitty-specs/`.
2. **Implement in a worktree**: feature work happens in `<project>-wtrees/<topic>/`; canonical repo directories stay on `main`.
3. **Validate locally**: run the owning repo's quality gate (`task quality`, `cargo test`, `cargo clippy`, Ruff, Vale, TruffleHog, cargo-deny, or repo-specific equivalents).
4. **Open PR**: branches use `feat/`, `fix/`, `chore/`, `ci/`, or `docs/` prefixes. Keep PRs focused to the owning component.
5. **Merge and publish**: merge to `main`, generate changelog/release notes from `cliff.toml` or repo-specific release tooling, then publish crates, binaries, web deploys, or container artifacts as appropriate.
6. **Propagate**: downstream repos consume new crate versions, package versions, generated clients, or commit references in follow-up PRs.
7. **Record**: update AgilePlus work-package state and add worklog entries for architecture, governance, dependency, integration, or research decisions.

GitHub Actions billing is constrained for this org, so CI failures caused only by runner billing limits are not treated as product failures; local quality gates remain authoritative.

## Key Invariants

- The shelf is a **polyrepo collection**; repo-local READMEs are authoritative for local build/run instructions.
- Shared behavior belongs in `phenoShared` or `phenotype-infrakit` before duplication is accepted in product repos.
- AgilePlus specs and work packages are first-class implementation inputs.
- Worktrees isolate feature work; canonical directories should remain integration/main checkouts.
- Cross-language boundaries should use explicit protocols: OpenAPI, Protobuf/gRPC, MCP schemas, or typed shared crates.
- UTF-8 markdown and documented release evidence are required for docs and governance artifacts.

## Per-repo Detail

Use this document for cross-repo boundaries. Use each repo README for local architecture, setup, and release commands:

| Project | Detail |
|---------|--------|
| AgilePlus | [AgilePlus/README.md](AgilePlus/README.md) |
| phenoShared | [phenoShared/README.md](phenoShared/README.md) |
| phenotype-infrakit | [phenotype-infrakit/README.md](phenotype-infrakit/README.md) |
| pheno-cli | [pheno-cli/README.md](pheno-cli/README.md) |
| pheno | [pheno/README.md](pheno/README.md) |
| thegent | [thegent/README.md](thegent/README.md) |
| helios-cli | [helios-cli/README.md](helios-cli/README.md) |
| heliosApp | [heliosApp/README.md](heliosApp/README.md) |
| AgentMCP | [AgentMCP/README.md](AgentMCP/README.md) |
| PhenoMCP | [PhenoMCP/README.md](PhenoMCP/README.md) |
| cheap-llm-mcp | [cheap-llm-mcp/README.md](cheap-llm-mcp/README.md) |
| agentapi-plusplus | [agentapi-plusplus/README.md](agentapi-plusplus/README.md) |
| cliproxyapi-plusplus | [cliproxyapi-plusplus/README.md](cliproxyapi-plusplus/README.md) |
| BytePort | [BytePort/README.md](BytePort/README.md) |
| FocalPoint | [FocalPoint/README.md](FocalPoint/README.md) |
| hwLedger | [hwLedger/README.md](hwLedger/README.md) |
| PolicyStack | [PolicyStack/README.md](PolicyStack/README.md) |
| phenoAI | [phenoAI/README.md](phenoAI/README.md) |
| tooling | [tooling/README.md](tooling/README.md) |
