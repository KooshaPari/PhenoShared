# AgilePlus FR/NFR Requirements Catalog

**Version:** 1.0.0  
**Date:** 2026-05-29  
**Status:** Backfilled from shipped session (PRs #574–#607) + forward gaps  
**Audience:** Tracera + AgilePlus system-of-record ingestion, future agents

---

## System Overview

AgilePlus is a hexagonal-architecture Rust workspace providing an agile project management backend with:
- A rich domain model (User, Project, Epic, Feature, Story, WorkPackage, Cycle, Module, Backlog)
- A GitHub sync adapter (octocrab) mapping issues/PRs to domain entities
- SQLite-backed persistence via repository ports
- NATS-based domain event bus
- Axum REST API with OpenAPI
- Clap CLI with sync subcommand
- P2P replication via mDNS discovery + vector-clock merge
- Application use-case layer wiring ports to adapters

**Workspace root:** `crates/`  
**Key crates:** `agileplus-domain`, `agileplus-application`, `agileplus-github`, `agileplus-sqlite`, `agileplus-events`, `agileplus-nats`, `agileplus-api`, `agileplus-cli`, `agileplus-p2p`, `agileplus-config`, `agileplus-import`

---

## Functional Requirements

### FR-AGP-001 — Domain Aggregate Model

| Field | Value |
|---|---|
| **ID** | FR-AGP-001 |
| **Title** | Rich domain aggregates with enforced invariants |
| **Description** | The system shall define User, Project, Epic, Feature, Story, WorkPackage, Cycle, Module, Backlog, and Governance aggregates as first-class domain types. Aggregates enforce business rules at construction time so illegal states are unrepresentable. |
| **Acceptance Criteria** | AC1: Project requires a non-empty name and valid owner; constructor returns `Result`. AC2: Story has a state machine with valid transitions only (see `state_machine.rs`). AC3: All aggregates derive `Debug`, `Clone`, `Serialize/Deserialize`. AC4: Domain events emitted on aggregate mutations. |
| **Status** | SHIPPED |
| **Traceability** | PRs #581, #595; `crates/agileplus-domain/src/domain/{project,epic,story,user,feature,work_package,cycle,module,backlog}.rs`; `crates/agileplus-domain/src/domain/state_machine.rs` |

---

### FR-AGP-002 — GitHub Repository Sync

| Field | Value |
|---|---|
| **ID** | FR-AGP-002 |
| **Title** | Sync GitHub issues and PRs into domain Stories/Features |
| **Description** | The system shall read GitHub issues and pull requests from a given repository via the octocrab client, map them to domain Story/Feature entities, and upsert them into the local store via the `SyncMappingRepository` port. |
| **Acceptance Criteria** | AC1: `GithubClient` authenticates via PAT from config (no hardcoded secrets). AC2: Issues are mapped to `Story`; PRs are mapped to `Feature`. AC3: Labels/milestone/assignees are captured. AC4: `SyncMapping` records GitHub ID → domain ID relationship. AC5: Repeated syncs are idempotent (upsert). |
| **Status** | SHIPPED |
| **Traceability** | PRs #592, #596, #597; `crates/agileplus-github/src/{client.rs,map.rs,sync.rs}`; `crates/agileplus-domain/src/domain/sync_mapping.rs` |

---

### FR-AGP-003 — SQLite Persistence

| Field | Value |
|---|---|
| **ID** | FR-AGP-003 |
| **Title** | Persist all domain aggregates to SQLite |
| **Description** | The system shall provide SQLite-backed implementations of all repository ports (User, Project, Epic, Feature, Story, WorkPackage, Cycle, Module, Backlog, SyncMapping, Event, Evidence, Metric) using `sqlx` with compile-time-checked queries and automatic migrations. |
| **Acceptance Criteria** | AC1: All repository traits defined in `agileplus-domain::ports` have a corresponding `SqliteXxxRepository` impl. AC2: Migrations run automatically on startup. AC3: CRUD operations return domain types (not DTOs). AC4: Repository impls are wired via the application composition root. |
| **Status** | SHIPPED |
| **Traceability** | PR #602; `crates/agileplus-sqlite/src/repository/{projects,epics,stories,users,features,work_packages,cycles,modules,sync_mappings,events,evidence,metrics}.rs`; `crates/agileplus-sqlite/src/lib/` (migrations) |

---

### FR-AGP-004 — Domain Event Publishing via NATS

| Field | Value |
|---|---|
| **ID** | FR-AGP-004 |
| **Title** | Publish typed domain events over NATS JetStream |
| **Description** | The system shall define a typed `DomainEvent` enum (StoryCreated, StoryTransitioned, EpicCreated, FeatureAdvanced, SyncCompleted, etc.) wrapped in an `EventEnvelope` with aggregate ID, timestamp, and correlation ID; publish these via a hexagonal `EventBus` port backed by a NATS JetStream adapter. |
| **Acceptance Criteria** | AC1: `EventBus` port defined in `agileplus-events`. AC2: `NatsAdapter` implements `EventBus`. AC3: Subject naming follows `agileplus.<aggregate>.<event>` convention. AC4: Envelope includes `aggregate_id`, `event_id` (UUID), `occurred_at`, `correlation_id`. AC5: Adapter is optional at runtime (degrades gracefully if NATS unreachable). |
| **Status** | SHIPPED |
| **Traceability** | PRs #600, #605; `crates/agileplus-events/src/{domain_event.rs,envelope.rs,handler.rs}`; `crates/agileplus-nats/src/{nats_adapter.rs,subject.rs,bus/bus.rs}` |

---

### FR-AGP-005 — Application Use-Case Layer

| Field | Value |
|---|---|
| **ID** | FR-AGP-005 |
| **Title** | Hexagonal use-case orchestration |
| **Description** | The system shall provide an `agileplus-application` crate with use-case structs that accept repository + event bus ports and orchestrate domain logic: CreateStory, CreateEpic, CreateFeature, AdvanceFeature, TransitionStory. Use cases return domain types and emit events. |
| **Acceptance Criteria** | AC1: Use cases depend only on port traits, never on adapter impls. AC2: Each use case has a single public `execute()` method. AC3: Use cases emit relevant `DomainEvent`s through the `EventBus` port. AC4: DTOs live in `agileplus-application::dto`, not in domain. |
| **Status** | SHIPPED |
| **Traceability** | PR #603; `crates/agileplus-application/src/use_cases/{create_story,create_epic,create_feature,advance_feature,transition_story}.rs`; `crates/agileplus-application/src/dto/` |

---

### FR-AGP-006 — REST API (CRUD + sync routes)

| Field | Value |
|---|---|
| **ID** | FR-AGP-006 |
| **Title** | Axum HTTP REST API for domain aggregates |
| **Description** | The system shall expose an Axum HTTP server with REST routes for Projects, Epics, Stories, Features, Cycles, Modules, Backlogs, WorkPackages, Governance, Branches/Worktrees, Import, Events, and a health endpoint. Routes delegate to application use-cases via the composition root `AppState`. |
| **Acceptance Criteria** | AC1: `GET /health` returns `200 OK` with uptime and version. AC2: CRUD routes exist for Project/Epic/Story (create, list, get-by-id). AC3: OpenAPI schema generated at startup via `utoipa`. AC4: No secrets in route handlers; auth tokens read from request headers or config. AC5: `AppState` is assembled at main() from adapters, not hardcoded. |
| **Status** | SHIPPED |
| **Traceability** | PRs #587, #606; `crates/agileplus-api/src/{router.rs,state.rs,routes/,middleware/,health.rs,openapi.rs}` |

---

### FR-AGP-007 — CLI Sync Subcommand

| Field | Value |
|---|---|
| **ID** | FR-AGP-007 |
| **Title** | CLI `sync` subcommand for GitHub repository ingestion |
| **Description** | The system shall provide an `agileplus-cli` binary with a `sync` subcommand accepting `--repo <owner/repo>` and `--project <id>` flags, invoking the GitHub sync service and printing a progress/summary report to stdout. |
| **Acceptance Criteria** | AC1: `agileplus sync --repo owner/repo --project <uuid>` runs without error on a valid PAT. AC2: Sync output shows counts: issues mapped, PRs mapped, new stories, updated stories. AC3: Errors (missing token, unreachable GitHub) exit with non-zero code and human-readable message. AC4: Config loaded from `.env` / env vars, not CLI flags for secrets. |
| **Status** | SHIPPED |
| **Traceability** | PRs #586, #601; `crates/agileplus-cli/src/{main.rs,commands/sync_cmd.rs,context.rs}` |

---

### FR-AGP-008 — P2P Peer Discovery and Replication

| Field | Value |
|---|---|
| **ID** | FR-AGP-008 |
| **Title** | mDNS peer discovery + vector-clock replication |
| **Description** | The system shall discover AgilePlus peers on the local network via mDNS, maintain a peer registry, and replicate domain state via a vector-clock-based merge protocol ensuring eventual consistency without a central coordinator. |
| **Acceptance Criteria** | AC1: `PeerDiscovery` service registers and discovers `_agileplus._tcp` mDNS service. AC2: `VectorClock` correctly computes happens-before and concurrent relationships. AC3: Replicated events are deduplicated by event ID. AC4: Conflict resolution is deterministic (last-writer-wins by wall-clock tiebreaker). |
| **Status** | SHIPPED |
| **Traceability** | PRs #591, #599; `crates/agileplus-p2p/src/{discovery.rs,vector_clock.rs,replication.rs,device.rs}` |

---

### FR-AGP-009 — Import / Export Pipeline

| Field | Value |
|---|---|
| **ID** | FR-AGP-009 |
| **Title** | Import projects from external manifest formats |
| **Description** | The system shall accept a manifest file describing a project structure (epics, stories, features) and import it into the domain model, producing an `ImportReport` with success/failure counts and error details. |
| **Acceptance Criteria** | AC1: `ImportReport` captures total, succeeded, failed item counts. AC2: Individual item import failures do not abort the entire import. AC3: Unit tests cover `ImportReport` construction and error accumulation. |
| **Status** | SHIPPED |
| **Traceability** | PR #590; `crates/agileplus-import/src/{importer/,manifest.rs,report.rs}` |

---

### FR-AGP-010 — Config Builder Macro

| Field | Value |
|---|---|
| **ID** | FR-AGP-010 |
| **Title** | `config_builder!` macro for zero-boilerplate config structs |
| **Description** | The system shall provide a `config_builder!` declarative macro in `agileplus-config` that generates typed config structs with env-var loading, defaults, and validation from a single declaration, eliminating duplicated config wiring across crates. |
| **Acceptance Criteria** | AC1: Macro replaces at least 3 previously duplicated config sites. AC2: Generated structs load values from env vars with documented fallback defaults. AC3: Missing required values produce a compile-time or startup error with the var name. |
| **Status** | SHIPPED |
| **Traceability** | PR #607; `crates/agileplus-config/src/lib.rs` |

---

### FR-AGP-011 — gRPC Service Layer

| Field | Value |
|---|---|
| **ID** | FR-AGP-011 |
| **Title** | gRPC API surface for inter-service communication |
| **Description** | The system shall expose gRPC endpoints for domain operations using tonic, enabling programmatic consumption by other services in the Phenotype org. Build system must gracefully degrade when `protoc` is absent. |
| **Acceptance Criteria** | AC1: `build.rs` gates proto compilation on `protoc` availability — DONE (graceful-skip + hand-written stubs in `agileplus-proto`). AC2: `WorkItemsService` proto defined with `ListProjects`, `ListEpics`, `ListStories`, `SyncRepository` RPCs — DONE (`proto/agileplus/v1/work_items.proto`). AC3: `AgilePlusCoreService` + `WorkItemsService` tonic impls delegate to `StoragePort` (hexagonal) — DONE. AC4: 27 tests green (12 lib-unit + 10 integration + 5 pact-schema). |
| **Status** | SHIPPED |
| **Traceability** | PR #594 (build fix); feat/grpc-service; `crates/agileplus-proto/` (stub-mode proto crate); `crates/agileplus-grpc/src/work_items.rs` (WorkItemsService impl); `crates/agileplus-grpc/src/server/mod.rs` (AgilePlusCoreService impl); `proto/agileplus/v1/` (core.proto, common.proto, agents.proto, integrations.proto, work_items.proto); 27 tests passing. |

---

### FR-AGP-012 — API Authentication

| Field | Value |
|---|---|
| **ID** | FR-AGP-012 |
| **Title** | Bearer-token / API-key authentication on REST API routes |
| **Description** | All protected REST API routes require a valid bearer token or API key validated against a configured shared secret. Public routes (`/health`, `/detailed-health`, `/info`) remain unauthenticated. Token validation is isolated in a hexagonal `TokenVerifier` port trait so the backend (shared-secret, JWT, Authvault) can be swapped without touching route handlers. |
| **Acceptance Criteria** | AC1: Unauthenticated request to a protected route returns `401 Unauthorized`. AC2: Valid `Authorization: Bearer <token>` header grants access (200). AC3: Invalid bearer token returns `401`. AC4: `GET /health` (and other public routes) require no credentials. AC5: Token validation uses axum middleware, not per-handler logic. AC6: Default impl (`SharedSecretVerifier`) uses constant-time comparison to prevent timing attacks. AC7: Keys configured via `AGILEPLUS_API_KEY` env var (CSV for multiple keys). |
| **Status** | SHIPPED |
| **Traceability** | PR #614; `crates/agileplus-api/src/middleware/auth.rs` (`authorize` middleware); `crates/agileplus-api/src/middleware/token_verifier.rs` (`TokenVerifier` port + `SharedSecretVerifier` default impl); `crates/agileplus-api/src/state.rs` (`token_verifier: Arc<dyn TokenVerifier>` field); `crates/agileplus-api/src/router.rs` (protected routes wired to `authorize`); `crates/agileplus-api/tests/api_integration.rs` (18 integration tests including 4 FR-AGP-012-specific: `auth_no_token_returns_401`, `auth_valid_bearer_token_returns_200`, `auth_wrong_bearer_token_returns_401`, `auth_health_is_public_no_token_needed`). Follow-up: JWT/Authvault `TokenVerifier` adapter (new FR). |

---

### FR-AGP-013 — End-to-End Sync → SQLite Wiring

| Field | Value |
|---|---|
| **ID** | FR-AGP-013 |
| **Title** | GitHub sync service wired to SQLite persistence end-to-end |
| **Description** | The `sync_repository` service shall invoke the application use cases which call SQLite repository adapters, persisting synced Stories/Features durably. `PersistSyncedStories` is the application-layer bridge: it accepts the `Vec<Story>` produced by `sync_repository` and upserts each story via the `StoryRepository` port (keyed by `requirement_id` = `gh:issue:<n>` / `gh:pr:<n>`). The SQLite adapter's `upsert_story_by_requirement_id` fulfils idempotency at the persistence layer. |
| **Acceptance Criteria** | AC1: `PersistSyncedStories::execute` persists N stories via `StoryRepository::upsert_by_requirement_id`. AC2: Re-running with the same stories does not create duplicates (idempotent upsert by `requirement_id`). AC3: Stories without a `requirement_id` return `DomainError::Validation`, not silent data loss. AC4: Five unit tests (in-memory double, no I/O) cover: N stories persisted, idempotent re-sync, missing `requirement_id` error, empty list, skipped items not persisted. |
| **Status** | SHIPPED |
| **Traceability** | PRs #597, #602, #603, #606 (individual pieces); this PR (feat/sync-sqlite-persistence) — `crates/agileplus-application/src/use_cases/persist_synced_stories.rs`; 5 new tests in that module; `crates/agileplus-domain/src/ports/story.rs` (`upsert_by_requirement_id`); `crates/agileplus-sqlite/src/repository/stories.rs` (`upsert_story_by_requirement_id`) |

---

### FR-AGP-014 — Dashboard Frontend

| Field | Value |
|---|---|
| **ID** | FR-AGP-014 |
| **Title** | Web dashboard for project/backlog visualization |
| **Description** | The system shall serve a web dashboard displaying project hierarchy, sprint backlogs, and story state distributions wired to live SQLite-backed API data. |
| **Acceptance Criteria** | AC1: Dashboard fetches from `GET /api/dashboard/epics-stories.json`. AC2: Kanban board reflects live story states from SQLite. AC3: React frontend renders epics and stories with status-colored cards. |
| **Status** | SHIPPED |
| **Traceability** | PRs #577, #578 (file restore), #611 (live SQLite wiring); `crates/agileplus-dashboard/src/routes.rs` (epics_stories_json endpoint), `crates/agileplus-dashboard/web/src/main.tsx` (React kanban), `crates/agileplus-sqlite/src/bin/seed_db.rs` (seeding). |

---

### FR-AGP-018 — Plane.so Integration Adapter

| Field | Value |
|---|---|
| **ID** | FR-AGP-018 |
| **Title** | Plane.so REST API integration adapter for bi-directional work item sync |
| **Description** | The system shall expose a `PlaneClient` that bridges AgilePlus domain aggregates to the Plane.so REST API, enabling creation, update, and deletion of issues, modules, cycles, labels, and sub-issues in Plane from AgilePlus events. The adapter reads `PLANE_BASE_URL`, `PLANE_WORKSPACE`, `PLANE_API_KEY` from env vars. HTTP errors are surfaced as typed `anyhow::Error`. |
| **Acceptance Criteria** | AC1: `PlaneClient::new(base_url, workspace, api_key)` constructs a client with reqwest + rate-limiting. AC2: `create_work_item`, `update_work_item`, `list_work_items`, `create_sub_issue` cover the core CRUD surface. AC3: `create_module`, `update_module`, `delete_module`, `add_work_item_to_module` manage module lifecycle. AC4: `create_cycle`, `update_cycle`, `delete_cycle`, `add_work_item_to_cycle` manage cycle lifecycle. AC5: `sync_labels` and `get_labels` bridge AgilePlus label model. AC6: Wiremock-backed integration tests green. AC7: `state_mapper.rs` maps AgilePlus domain states to Plane state IDs. |
| **Status** | SHIPPED |
| **Traceability** | PRs #295, #464; `crates/agileplus-plane/src/client/` (PlaneClient + resources); `crates/agileplus-plane/src/state_mapper.rs`; `crates/agileplus-plane/src/outbound.rs`; `crates/agileplus-plane/src/sync.rs`; `crates/agileplus-plane/src/client/tests.rs` (wiremock tests). |

---

### FR-AGP-019 — Work-Item Dependency Graph

| Field | Value |
|---|---|
| **ID** | FR-AGP-019 |
| **Title** | Graph-layer dependency model for work items with blocking-path traversal |
| **Description** | The system shall expose a hexagonal `GraphStore` port over a directed graph of work item nodes and typed relationships (blocks, is-blocked-by, related, etc.). The port supports `upsert_node`, `create_relationship`, `delete_relationship`, `get_dependencies`, and `get_blocking_path` for chain traversal. |
| **Acceptance Criteria** | AC1: `GraphStore` trait is async-trait object-safe. AC2: `InMemoryGraphStore` fully implements all port methods. AC3: `get_dependencies(id)` returns all directly-dependent node UUIDs. AC4: `get_blocking_path(id)` returns the full upstream blocking chain. AC5: `upsert_node` is idempotent by UUID. AC6: Node types and relationship types are enum-typed (`NodeType`, `RelType`). |
| **Status** | SHIPPED |
| **Traceability** | PRs #326, #336; `crates/agileplus-graph/src/graph_store.rs` (GraphStore trait + InMemoryGraphStore); `crates/agileplus-graph/src/types.rs` (Node, Relationship, NodeType, RelType). |

---

### FR-AGP-016 — CLI Read/List Subcommands

| Field | Value |
|---|---|
| **ID** | FR-AGP-016 |
| **Title** | CLI `list` subcommands for projects, epics, and stories |
| **Description** | The system shall provide three read-only `list` subcommands in `agileplus-cli`: `list-projects` (all projects), `list-epics [--project <id>]` (all epics, optionally filtered by project), and `list-stories [--epic <id>] [--status <s>]` (stories filtered by epic and/or lifecycle status). Each subcommand defaults to a human-readable table and accepts `--json` to emit pretty-printed JSON. Storage is read from the SQLite adapter via the `StoragePort` port; the database path is resolved from the `AGILEPLUS_DB` environment variable (default: `agileplus.db`). |
| **Acceptance Criteria** | AC1: `agileplus list-projects` prints a table of all projects or "No projects found." AC2: `agileplus list-epics --project <id>` returns only epics for that project. AC3: `agileplus list-stories --epic <id> --status <s>` filters by both dimensions independently. AC4: `--json` flag emits valid JSON on all three subcommands. AC5: Invalid `--status` value exits with a non-zero code and an error message. AC6: All five acceptance criteria are covered by in-memory unit tests (no real I/O). |
| **Status** | SHIPPED |
| **Traceability** | feat/cli-list-commands; `crates/agileplus-cli/src/commands/list_projects.rs`; `crates/agileplus-cli/src/commands/list_epics.rs`; `crates/agileplus-cli/src/commands/list_stories.rs`; `crates/agileplus-cli/src/commands/list_tests.rs` (10 unit tests); `crates/agileplus-domain/src/ports/agent.rs` (new port stub); `crates/agileplus-domain/src/domain/governance.rs` (`BuiltinPolicy`); `crates/agileplus-domain/src/domain/sync_mapping.rs` (`SyncMapping::new`). |

---

### FR-AGP-015 — OpenTelemetry Observability

| Field | Value |
|---|---|
| **ID** | FR-AGP-015 |
| **Title** | OpenTelemetry traces + metrics export via OTLP |
| **Description** | The system shall instrument the Axum API with a per-request tracing span (method, path, status, duration) and initialise an OTLP exporter pointed at `OTEL_EXPORTER_OTLP_ENDPOINT`. When no endpoint is configured the system runs in no-op mode (no network connection, no errors). The wiring is hexagonal: a thin `agileplus-telemetry` init module configures the global `tracing` subscriber with an optional `tracing-opentelemetry` layer; business logic is not polluted with OTel calls. |
| **Acceptance Criteria** | AC1: `OTEL_EXPORTER_OTLP_ENDPOINT` absent → subscriber initialises successfully with no-op provider. AC2: `TelemetryAdapter::noop()` implements `ObservabilityPort` without panicking. AC3: `init_telemetry(TelemetryConfig::default())` returns `Ok(TelemetryGuard)`. AC4: `OtelTracingLayer` middleware wraps an axum handler without disrupting the response. AC5: W3C `traceparent` header propagates through middleware without panic. |
| **Status** | SHIPPED |
| **Traceability** | feat/opentelemetry; `crates/agileplus-telemetry/src/lib.rs` (`init_subscriber`, `SubscriberGuard`), `src/adapter.rs` (`TelemetryAdapter`, `TelemetryGuard`, `init_telemetry`), `src/traces/mod.rs` (`telemetry_layer`), `src/config.rs` (`TelemetryConfig`); `crates/agileplus-api/src/middleware/otel.rs` (`OtelTracingLayer`, `opentelemetry_tracing_layer`); 33 unit tests in `agileplus-telemetry`, 2 new integration tests in `agileplus-api`. Crates: `tracing 0.1`, `tracing-subscriber 0.3`, `tracing-opentelemetry 0.28`, `opentelemetry 0.27`, `opentelemetry_sdk 0.27`, `opentelemetry-otlp 0.27` (http-proto + reqwest). |

---

### FR-AGP-017 — Triage Automation (Rule-Based Classify for Synced Items)

| Field | Value |
|---|---|
| **ID** | FR-AGP-017 |
| **Title** | Rule-based triage engine for synced GitHub items |
| **Description** | Given a synced item (title / body / labels), the system shall apply a configurable, ordered rule set to assign a `BacklogPriority` and `Intent` (category). Rules are data-driven (`TriageRules` config struct with ordered `Vec<TriageRule>`); first match wins. A pure `classify(item, rules) -> TriageOutcome` function is the hexagonal port — no I/O, no side effects. Default rules ship with the crate: bug/crash keywords → `High` + `Bug`; docs keywords → `Low` + `Docs`; feature keywords → `Medium` + `Feature`; unmatched → `Medium` + `Task`. The domain `Intent` enum is extended with a `Docs` variant; `Intent::default_priority()` and `BacklogItem::from_triage()` are promoted to the domain crate. |
| **Acceptance Criteria** | AC1: bug/crash keyword in title, body, or label → `BacklogPriority::High` + `Intent::Bug`. AC2: docs/documentation keyword or label → `BacklogPriority::Low` + `Intent::Docs`. AC3: No matching rule → `BacklogPriority::Medium` + `Intent::Task` (configurable default). AC4: Rule precedence: first matching rule in the ordered list wins (bug rule fires before docs when both terms appear). AC5: Empty input (`SyncedItem::default()`) returns the configured default without panic. AC6: Custom `TriageRules` override all built-in behaviours. AC7: `cargo test -p agileplus-triage` green; `cargo check --workspace` green. |
| **Status** | SHIPPED |
| **Traceability** | feat/triage-automation; `crates/agileplus-triage/src/engine.rs` (`SyncedItem`, `TriageRules`, `TriageRule`, `TriageOutcome`, `classify`); `crates/agileplus-triage/src/lib.rs` (module wiring + re-exports); `crates/agileplus-domain/src/domain/backlog.rs` (`Intent::Docs` variant, `Intent::default_priority`, `BacklogItem::from_triage`); `crates/agileplus-sqlite/src/repository/backlog.rs` (`intent_str` extended); 37 tests passing (9 engine unit + 7 classifier unit + 5 backlog unit + 9 adapter unit + 4 router unit + 1 doctest). |

---

## Non-Functional Requirements

### NFR-AGP-001 — Hexagonal Architecture

| Field | Value |
|---|---|
| **ID** | NFR-AGP-001 |
| **Title** | Strict ports-and-adapters separation |
| **Description** | Domain and application crates shall not depend on infrastructure crates. Adapters (SQLite, NATS, GitHub) implement port traits defined in `agileplus-domain::ports` and `agileplus-events`. No adapter type ever appears in domain or application crate signatures. |
| **How Met** | `agileplus-domain` has no dep on `agileplus-sqlite`, `agileplus-nats`, or `agileplus-github`. Application crate depends on domain ports only. Composition root in `agileplus-api::state` performs the wiring. |
| **Evidence** | `crates/agileplus-domain/Cargo.toml` (no infra deps); `crates/agileplus-domain/src/ports/` (trait-only); PR #603, #605, #606 |

---

### NFR-AGP-002 — Illegal States Unrepresentable

| Field | Value |
|---|---|
| **ID** | NFR-AGP-002 |
| **Title** | Domain invariants enforced at type level |
| **Description** | Aggregates use private fields + constructors returning `Result` for invariant validation. The Story state machine uses an enum-based transition table rejecting invalid transitions at runtime before mutation. |
| **How Met** | Project constructor validates non-empty name/owner. `state_machine.rs` defines allowed transitions as a match table. All invalid transitions return `Err`. |
| **Evidence** | `crates/agileplus-domain/src/domain/state_machine.rs`; `crates/agileplus-domain/src/domain/project.rs`; PR #595 |

---

### NFR-AGP-003 — No Hardcoded Secrets

| Field | Value |
|---|---|
| **ID** | NFR-AGP-003 |
| **Title** | All secrets and config via environment variables |
| **Description** | GitHub PATs, NATS credentials, DB paths, and API keys are loaded exclusively from environment variables or `.env` files. No secrets appear in source or committed config files. |
| **How Met** | `agileplus-github::config` loads `GITHUB_TOKEN` from env. `agileplus-nats::config` loads `NATS_URL`. `config_builder!` macro enforces env-var sourcing. `.env.example` is the only committed secrets reference. |
| **Evidence** | `crates/agileplus-github/src/config.rs`; `crates/agileplus-nats/src/config.rs`; PR #607 (`config_builder!`); PR #574 (CVE-aware dep bumps) |

---

### NFR-AGP-004 — Workspace Builds Clean

| Field | Value |
|---|---|
| **ID** | NFR-AGP-004 |
| **Title** | `cargo build --workspace` succeeds with no errors or warnings-as-errors |
| **Description** | CI must pass `cargo build --workspace` and `cargo test --workspace` on every merge to main. All 27 crates must compile. gRPC build gracefully degrades when `protoc` is absent. |
| **How Met** | CI workflow uses `ubuntu-24.04` with explicit workspace member declarations. PR #594 added `tonic-build` as build-dep with graceful protoc gate. PR #583 scaffolded 9 missing stub crates. PR #582 fixed workspace member list. |
| **Evidence** | `.github/workflows/`; PRs #582, #583, #584, #594, #598 |

---

### NFR-AGP-005 — Test Coverage at Unit Layer

| Field | Value |
|---|---|
| **ID** | NFR-AGP-005 |
| **Title** | Unit tests for all domain + application logic |
| **Description** | All domain aggregates, use cases, and import pipeline components shall have unit tests. Tests use only in-memory/mock adapters; no real I/O in unit tests. |
| **How Met** | `agileplus-import` has unit tests for `ImportReport`. `agileplus-sqlite` has embedded tests. Domain crates have `#[cfg(test)]` modules. Fixtures crate provides shared test data. |
| **Evidence** | PR #590; `crates/agileplus-sqlite/src/tests.rs`; `crates/agileplus-fixtures/`; `crates/agileplus-contract-tests/` |

---

### NFR-AGP-006 — CVE-Aware Dependency Management

| Field | Value |
|---|---|
| **ID** | NFR-AGP-006 |
| **Title** | All dependencies on latest stable, no known active CVEs |
| **Description** | Rust workspace dependencies are bumped to latest stable on each session. Python dispatch-mcp dependencies follow the same policy. Downgrades are annotated with CVE ID in commit message. |
| **How Met** | PR #574 bumped vulnerable Rust deps. PR #593 bumped `fastmcp` from 2.14.7 → 3.2.0. |
| **Evidence** | PRs #574, #593; `Cargo.lock`; `dispatch-mcp/pyproject.toml` |

---

### NFR-AGP-007 — Eventual Consistency via P2P Replication

| Field | Value |
|---|---|
| **ID** | NFR-AGP-007 |
| **Title** | Multi-node deployments converge to consistent state |
| **Description** | The P2P replication layer guarantees eventual consistency: any two nodes that receive the same set of events will converge to identical state, regardless of delivery order. |
| **How Met** | Vector-clock based merge in `agileplus-p2p`. Events are identified by UUID; deduplication prevents double-apply. Conflict resolution is deterministic. |
| **Evidence** | PRs #591, #599; `crates/agileplus-p2p/src/vector_clock.rs`; `crates/agileplus-p2p/src/replication.rs` |

---

## Gaps / Forward FRs Summary

| ID | Title | Status |
|---|---|---|
| FR-AGP-011 | gRPC service definitions + impl | PARTIAL (build fix only) |
| FR-AGP-012 | API bearer-token authentication | SHIPPED |
| FR-AGP-013 | End-to-end sync → SQLite wiring | SHIPPED |
| FR-AGP-014 | Live dashboard frontend | SHIPPED (PR #611) |
| FR-AGP-016 | CLI `list` subcommands (projects, epics, stories) | SHIPPED |
| FR-AGP-015 | Observability: OpenTelemetry traces + metrics export | SHIPPED (feat/opentelemetry) |
| FR-AGP-017 | Triage automation — rule-based classify for synced items | SHIPPED (feat/triage-automation) |
| FR-AGP-018 | Plane.so integration adapter | SHIPPED (`crates/agileplus-plane/`; PlaneClient + resources: work_items, modules, cycles, labels; sync outbound; wiremock tests) |
| FR-AGP-019 | Graph/dependency analysis for work items | SHIPPED (`crates/agileplus-graph/`; InMemoryGraphStore; get_dependencies + get_blocking_path; UUID-based graph API) |

---

## Traceability Matrix (PR → FRs)

| PR | Title (condensed) | Satisfies |
|---|---|---|
| #574 | Security: bump vulnerable deps | NFR-AGP-006 |
| #575 | Docs: tooling reference | (docs only) |
| #577, #578 | Restore dashboard + sibling crates | FR-AGP-014 (partial) |
| #581 | Domain scaffold: aggregate types + ports | FR-AGP-001 |
| #582, #583, #584 | CI fixes, workspace members, stub crates | NFR-AGP-004 |
| #585 | Domain events + dashboard templates sync | FR-AGP-001 |
| #586 | CLI bootstrap (clap + in-memory mock) | FR-AGP-007 |
| #587 | API bootstrap (axum server) | FR-AGP-006 |
| #589 | Fix duplicate domain.rs (E0761) | NFR-AGP-004 |
| #590 | Unit tests for ImportReport | FR-AGP-009, NFR-AGP-005 |
| #591 | P2P mDNS peer discovery | FR-AGP-008 |
| #592 | GitHub octocrab read client | FR-AGP-002 |
| #593 | Bump fastmcp 2.14.7 → 3.2.0 | NFR-AGP-006 |
| #594 | gRPC tonic-build dep + protoc gate | FR-AGP-011, NFR-AGP-004 |
| #595 | User/Epic/Story aggregates; harden Project | FR-AGP-001, NFR-AGP-002 |
| #596 | GitHub → domain mapping | FR-AGP-002 |
| #597 | sync_repository capstone service | FR-AGP-002, FR-AGP-013 |
| #598 | Hygiene: lib.rs conflict, lock update | NFR-AGP-004 |
| #599 | P2P vector-clock replication | FR-AGP-008, NFR-AGP-007 |
| #600 | DomainEvent enum + EventEnvelope + EventHandler | FR-AGP-004 |
| #601 | CLI sync subcommand | FR-AGP-007 |
| #602 | SQLite-backed repositories | FR-AGP-003 |
| #603 | Application use-case layer | FR-AGP-005 |
| #605 | NATS hexagonal adapter | FR-AGP-004 |
| #606 | Wire use-cases into AppState | FR-AGP-005, FR-AGP-006 |
| #607 | config_builder! macro | FR-AGP-010, NFR-AGP-003 |
| feat/sync-sqlite-persistence | PersistSyncedStories use case + 5 tests | FR-AGP-013, NFR-AGP-005 |
| feat/opentelemetry | OTel subscriber init + OTLP adapter + request-span middleware + 35 tests | FR-AGP-015, NFR-AGP-004 |
| feat/cli-list-commands | CLI list-projects / list-epics / list-stories subcommands + 10 unit tests + domain stubs (AgentPort, BuiltinPolicy, SyncMapping::new) | FR-AGP-016, NFR-AGP-005 |
| feat/triage-automation | Rule-based triage engine (engine.rs) + domain Intent::Docs + default_priority + from_triage + 37 tests | FR-AGP-017, NFR-AGP-005 |
| #611 | Dashboard live wiring — epics_stories_json endpoint + React kanban + seed_db binary | FR-AGP-014 |
| #295, #464 | Plane.so PlaneClient + resources (work_items, modules, cycles, labels) + state_mapper + sync outbound | FR-AGP-018 |
| #326, #336 | agileplus-graph crate — GraphStore trait + InMemoryGraphStore + UUID-based API | FR-AGP-019 |

---

## Rich Media Stubs

<!-- RICH-MEDIA-STUB type="annotated-screenshot" subject="FR/NFR requirements panel — AgilePlus spec-driven view" journey="" status="PUBLISHED" -->
![AgilePlus Epics panel — each epic mapped to FR/NFR requirement IDs with per-epic story rollup](../assets/rich-media/agileplus/requirements-epics-panel.png)

*Captured via `@phenotype/doc-embeds` Playwright helper (`requirements-epics-panel.png`). Each epic carries its backlog state and `requirement_id` traceability link to the FR/NFR IDs in this catalog; story rollup counts feed dashboard KPIs when `API_PORT=4000` is running.*
<!-- END-RICH-MEDIA-STUB -->
