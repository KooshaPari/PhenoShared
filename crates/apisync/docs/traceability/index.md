# Traceability

> Traceability identifier: **HD-005** (see `.health-dashboard.yml`)

This page maps every requirement to the code and tests that implement and
verify it, so a change can be traced from requirement → implementation → test.

<TraceabilityMatrix
  :features="[
    { id: 'REQ-001', name: 'REST CRUD', tests: ['rest_integration_tests.rs'], code: ['src/endpoints.rs', 'src/adapters/rest/hyper_server.rs'], coverage: 90 },
    { id: 'REQ-002', name: 'Health probes', tests: ['src/endpoints.rs (unit)'], code: ['src/endpoints.rs'], coverage: 95 },
    { id: 'REQ-003', name: 'GraphQL', tests: ['src/adapters/graphql/'], code: ['src/adapters/graphql/'], coverage: 85 },
    { id: 'REQ-004', name: 'WebSocket', tests: ['src/adapters/websocket/'], code: ['src/adapters/websocket/'], coverage: 80 },
    { id: 'REQ-005', name: 'Middleware', tests: ['src/domain/middleware/'], code: ['src/domain/middleware.rs'], coverage: 90 },
    { id: 'REQ-006', name: 'Logging', tests: ['src/infrastructure/logging.rs'], code: ['src/infrastructure/logging.rs'], coverage: 95 },
    { id: 'REQ-007', name: 'Property invariants', tests: ['tests/property_tests.rs'], code: ['src/domain/mod.rs'], coverage: 75 },
  ]"
/>

## Requirements

| ID      | Requirement                                          | Status         | Implementation                                                    | Tests                                          |
| ------- | ---------------------------------------------------- | -------------- | ----------------------------------------------------------------- | ---------------------------------------------- |
| REQ-001 | REST CRUD over the Item model                        | ✅ Implemented | `endpoints::ItemCrudEndpoint`, `adapters::rest::HyperServer`      | `tests/rest_integration_tests.rs`              |
| REQ-002 | Liveness/readiness probes                            | ✅ Implemented | `endpoints::{HealthzEndpoint, ReadyzEndpoint}`                    | unit tests in `src/endpoints.rs`               |
| REQ-003 | GraphQL schema + query/mutation/subscription         | ✅ Implemented | `adapters::graphql::{build_schema, GraphQLEndpoint}`              | `src/adapters/graphql/` unit tests             |
| REQ-004 | WebSocket connection management + broadcast          | ✅ Implemented | `adapters::websocket::{WebSocketServer, BroadcastHub, WsMessage}` | `src/adapters/websocket/` unit tests           |
| REQ-005 | Composable middleware chain + request-id propagation | ✅ Implemented | `domain::middleware::{Middleware, Next, RequestIdMiddleware}`     | `src/domain/middleware/` unit tests            |
| REQ-006 | Structured logging initialization                    | ✅ Implemented | `infrastructure::logging::init()`                                 | `src/infrastructure/logging.rs` unit tests     |
| REQ-007 | Store invariants hold under random input             | ✅ Implemented | `domain::ItemStore`                                               | `tests/property_tests.rs`                      |
| REQ-008 | Request body size cap (memory DoS protection)        | ✅ Implemented | `adapters::rest::MAX_REQUEST_BODY_BYTES`                          | `src/adapters/rest/hyper_server.rs` unit tests |
| REQ-009 | Stable public API surface (no glob re-exports)       | ✅ Implemented | `src/lib.rs` explicit prelude                                     | compile tests / docs                           |
| REQ-010 | Coverage regression must fail the gate               | ✅ Implemented | `quality-gate.yml` (85% threshold)                                | CI gate                                        |

## Quality gates (from `.health-dashboard.yml`)

| Dimension     | Weight | Gate                                                                | Status                                        |
| ------------- | ------ | ------------------------------------------------------------------- | --------------------------------------------- |
| Documentation | 15     | CLAUDE.md, README.md, CONTRIBUTING.md, LICENSE, CHANGELOG.md        | ✅ Present                                    |
| Test coverage | 20     | ≥80% line / ≥70% branch (codecov)                                   | ✅ Enforced by quality gate                   |
| Security      | 25     | cargo-audit, cargo-deny, trivy                                      | ✅ `cargo-deny.yml`, `security-deep-scan.yml` |
| Dependencies  | 15     | freshness ≤90d, outdated tolerance 5                                | ✅ Renovate/dependabot                        |
| Compliance    | 15     | deny.toml, clippy.toml, pre-commit, codecov.yml, toolchain, nextest | ✅ Present                                    |
| Code quality  | 10     | clippy, rustfmt                                                     | ✅ CI + Trunk                                 |

<TestCoverageBadge :overall="90" :unit="95" />
