# FR-GRPC-001 — AgilePlus gRPC Service Surface

> Spec anchor: `specs/013-agileplus-grpc/`
> Status: PROPOSED → accepted on `cargo test -p agileplus-grpc` pass
> Crate: `agileplus-grpc` (with `agileplus-proto` for schema)

## Description

The `agileplus-grpc` adapter exposes the AgilePlus application port layer
over a tonic gRPC server, sharing `agileplus-proto` schemas with any
remote-language client. Health, reflection, and bidirectional streaming
for events are first-class. Server errors map to canonical gRPC status
codes; the integration test suite proves request/response parity with
the HTTP adapter in `agileplus-api`.

## Acceptance Criteria

| AC  | Criterion |
|-----|-----------|
| AC1 | gRPC service `AgilePlusService` implements at least one unary and one streaming method. |
| AC2 | Health check returns SERVING when dependencies are healthy. |
| AC3 | Reflection is enabled and lists every registered service. |
| AC4 | Domain errors map to canonical gRPC status codes (NOT_FOUND, INVALID_ARGUMENT, etc.). |
| AC5 | Proto schemas live in `agileplus-proto` and are generated, never hand-edited. |
| AC6 | `agileplus-grpc` and `agileplus-api` share request/response shapes for parity. |
| AC7 | TLS termination is configurable; insecure mode is only available in dev/test. |
| AC8 | `grpc_integration.rs` proves ACs above with at least one assertion per AC. |

## Traceability

- Spec: `specs/013-agileplus-grpc/`
- Code: `crates/agileplus-grpc/src/`, `crates/agileplus-proto/src/`
- BDD: `specs/013-agileplus-grpc/bdd/`
- Tests: `crates/agileplus-grpc/tests/grpc_integration.rs`
- Journey: `docs/journeys/grpc-roundtrip.md`
