# Project Dependencies

**Project**: AgilePlus  
**Classification**: Tier 2 - Platform Infrastructure  
**Last Updated**: 2026-04-02

## Overview

Project management platform with hybrid Rust/Python architecture.

## Workspace Structure

| Member | Path | Purpose |
|--------|------|---------|
| nexus | `libs/nexus` | Core library |
| plugin-registry | `libs/plugin-registry` | Plugin system |
| plugin-sample | `libs/plugin-sample` | Example plugin |
| plugin-cli | `libs/plugin-cli` | CLI plugin |
| plugin-git | `libs/plugin-git` | Git integration |
| plugin-grpc | `libs/plugin-grpc` | gRPC plugin |
| plugin-integration | `libs/plugin-integration` | Integration tests |
| intent-registry | `libs/intent-registry` | Intent management |
| health-monitor | `libs/health-monitor` | Health checks |
| logger | `libs/logger` | Logging |
| metrics | `libs/metrics` | Metrics collection |
| config-core | `libs/config-core` | Configuration |
| tracing-core | `libs/tracing-core` | Distributed tracing |
| cli-framework | `libs/cli-framework` | CLI infrastructure |
| hexagonal-rs | `libs/hexagonal-rs` | Hexagonal patterns |
| hexkit | `libs/hexkit` | Hexagonal utilities |
| cipher | `libs/cipher` | Encryption |
| gauge | `libs/gauge` | Metrics |
| xdd-lib-rs | `libs/xdd-lib-rs` | XDD library |

## Workspace Crate Dependencies

| Crate | Path | Purpose |
|-------|------|---------|
| agileplus-api | `crates/agileplus-api` | API layer |
| agileplus-cli | `crates/agileplus-cli` | CLI |
| agileplus-domain | `crates/agileplus-domain` | Domain logic |
| agileplus-fixtures | `crates/agileplus-fixtures` | Test fixtures |
| agileplus-grpc | `crates/agileplus-grpc` | gRPC service |
| agileplus-sqlite | `crates/agileplus-sqlite` | SQLite adapter |
| agileplus-plane | `crates/agileplus-plane` | Plane integration |
| agileplus-telemetry | `crates/agileplus-telemetry` | Observability |
| agileplus-triage | `crates/agileplus-triage` | Triage system |
| agileplus-events | `crates/agileplus-events` | Event sourcing |
| agileplus-cache | `crates/agileplus-cache` | Caching |
| agileplus-subcmds | `crates/agileplus-subcmds` | Subcommands |
| agileplus-graph | `crates/agileplus-graph` | Graph operations |
| agileplus-nats | `crates/agileplus-nats` | NATS integration |
| agileplus-sync | `crates/agileplus-sync` | Sync engine |
| agileplus-dashboard | `crates/agileplus-dashboard` | Dashboard |
| agileplus-github | `crates/agileplus-github` | GitHub integration |
| agileplus-p2p | `crates/agileplus-p2p` | P2P networking |
| agileplus-integration-tests | `crates/agileplus-integration-tests` | Integration tests |
| agileplus-contract-tests | `crates/agileplus-contract-tests` | Contract tests |
| agileplus-benchmarks | `crates/agileplus-benchmarks` | Benchmarks |

## Workspace Dependencies

| Crate | Version | Features |
|-------|---------|----------|
| serde | 1 | derive |
| serde_json | 1 | - |
| toml | 0.8 | - |
| chrono | 0.4 | serde |
| sha2 | 0.10 | - |
| tokio | 1 | full |
| thiserror | 2 | - |
| anyhow | 1 | - |
| tracing | 0.1 | - |
| tracing-subscriber | 0.3 | - |
| tracing-opentelemetry | 0.32 | - |
| futures-util | 0.3 | - |
| axum | 0.8 | json, macros |
| tonic | 0.13 | transport |
| tonic-build | 0.13 | prost |
| prost | 0.13 | - |
| opentelemetry | 0.31 | trace, metrics |
| opentelemetry-otlp | 0.31 | trace, metrics, http-proto |

## Python Dependencies

Located in `python/` directory with separate pyproject.toml.

## Platform Integrations

| Platform | Integration |
|----------|--------------|
| thegent | Agent orchestration |
| Plane | Deployment platform |
| NATS | Event streaming |
| GitHub | Repository operations |

## External Services

| Service | Purpose |
|---------|---------|
| SQLite | Primary database |
| gRPC | Internal communication |
| HTTP API | External API |

## Dependency Policy

- **Security patches**: Within 24 hours
- **Rust updates**: Weekly via `cargo update`
- **Major version upgrades**: Quarterly review

## Constraints

- Rust 1.85+ required
- Uses workspace-level dependency management
- Locked to tonic 0.13 for gRPC stability
