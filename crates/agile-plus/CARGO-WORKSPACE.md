# AgilePlus Cargo Workspace

This workspace contains the Rust implementation of AgilePlus: domain models,
application services, infrastructure adapters, transport surfaces, and developer
tooling for the `agileplus` CLI and companion services.

## Workspace Map

| Area | Crates | Role |
| --- | --- | --- |
| Domain and application | `agileplus-domain`, `agileplus-application`, `agileplus-config`, `agileplus-events`, `agileplus-proto`, `agileplus-fixtures` | Pure domain types, use cases, configuration, event sourcing, generated protobuf types, and deterministic test data. |
| Infrastructure adapters | `agileplus-sqlite`, `agileplus-cache`, `agileplus-git`, `agileplus-nats`, `agileplus-telemetry`, `agileplus-import` | Persistence, cache, VCS, pub/sub, observability, and import/reporting adapters. |
| Interfaces | `agileplus-api`, `agileplus-grpc`, `agileplus-dashboard`, `agileplus-github`, `agileplus-plane`, `agileplus-p2p`, `agileplus-triage` | HTTP, gRPC, dashboard, external sync, peer replication, and triage surfaces. |
| Operations and DX | `agileplus-cli`, `agileplus-governance`, `xtask-anti-patterns` | CLI entrypoint, governance policy/audit tooling, and workspace linting. |

## Public API Index

- `agileplus-api`: `create_router`, `AppState`, API key, middleware, OpenAPI, responses, routes, and router modules.
- `agileplus-application`: `dto`, `error`, `events`, and `use_cases` modules for hexagonal use-case orchestration.
- `agileplus-cache`: `CacheConfig`, `CacheHealthChecker`, `RateLimiter`, `CachePool`, `ProjectionCache`, and cache store types.
- `agileplus-cli`: command context types and CLI command modules used by the `agileplus` binary.
- `agileplus-config`: `config_builder!` macro support and re-exported `paste`.
- `agileplus-dashboard`: dashboard app state, health, process detection, routes, seed helpers, and templates.
- `agileplus-domain`: config, credentials, domain types, errors, and port traits.
- `agileplus-events`: domain events, hash-chain helpers, query/replay/snapshot APIs, event store traits, and in-memory store.
- `agileplus-fixtures`: `FeatureBuilder`, `WorkPackageBuilder`, dogfood seed data, payload builders, and `TestFixtures`.
- `agileplus-git`: `GitVcsAdapter` VCS implementation.
- `agileplus-github`: REST client, GitHub-to-domain mapping, and repository sync APIs.
- `agileplus-governance`: `GovernanceClient`, release channels, audit logger, policy engine, rate limiter, config, and errors.
- `agileplus-grpc`: gRPC conversions, event bus, proxy, streaming, work-items services, and `start_server`.
- `agileplus-import`: `ImportReport` and import reporting module.
- `agileplus-nats`: `EventBus`, `InMemoryBus`, `NatsEventBus`, `Subject`, `Envelope`, handlers, health, and config.
- `agileplus-p2p`: `P2pNode`, `P2pBehaviour`, `PeerId`, `P2pError`, discovery, replication, vector clock, device, export/import, and git merge modules.
- `agileplus-plane`: Plane client, state mapper, webhook, inbound/outbound sync, content hash, label sync, runtime, and sync queue APIs.
- `agileplus-proto`: generated or stubbed `agileplus` protobuf/tonic module.
- `agileplus-sqlite`: `SqliteStorageAdapter`, migrations, rebuild, repository, and seed modules.
- `agileplus-telemetry`: `init_telemetry`, `TelemetryAdapter`, `TelemetryGuard`, `TelemetryConfig`, logging helpers, metrics, traces, and `init_subscriber`.
- `agileplus-triage`: `classify`, `SyncedItem`, `TriageOutcome`, `TriageRule`, `TriageRules`, and backlog store operations.
- `xtask-anti-patterns`: workspace anti-pattern linter binary.

## Common Commands

```bash
cargo build --workspace --all-targets
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
cargo run -p xtask-anti-patterns
```

Run crate-specific tests with `cargo test -p <crate-name>`.

