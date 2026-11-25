# ADR-001: Choice of Hexagonal Architecture

## Status

Accepted

## Context

Apisync is a universal API toolkit that must support REST, GraphQL, and WebSocket transports while remaining testable, evolvable, and maintainable. The codebase is organized around a layered architecture where domain logic, application use cases, transport adapters, and infrastructure concerns are separated. We needed a structural paradigm that makes dependencies point inward (toward domain logic) and keeps transport details substitutable without cascading changes.

Alternatives considered:
- **Layered (n-tier) architecture**: common in enterprise code, but lower layers often depend on upper layers (e.g., domain types importing HTTP headers), which undermines testability.
- **Micro-kernel / plugin architecture**: powerful for runtime extensibility, but adds indirection and dynamic-loading complexity that we do not need for a compile-time crate.
- **Flat module structure**: simplest for small projects, but leads to implicit coupling as the surface area grows.

## Decision

Adopt **hexagonal architecture** (ports and adapters) as the primary structural pattern.

- `domain/` — transport-agnostic request/response types, traits, and business rules.
- `application/` — use case orchestration that depends only on `domain`.
- `adapters/` — concrete implementations for REST (hyper), GraphQL (async-graphql), and WebSocket (tokio-tungstenite).
- `infrastructure/` — cross-cutting concerns such as logging, configuration, and telemetry.

All dependency arrows point inward: `adapters` -> `application` -> `domain`. `infrastructure` is injected, never imported directly by `domain` or `application`.

## Consequences

- **Positive**: Unit tests can run against `domain` and `application` without bringing up HTTP servers, GraphQL schemas, or WebSocket connections.
- **Positive**: Swapping a transport adapter (e.g., hyper for reqwest, or axum for REST) requires changes only in `adapters/rest/`, leaving public APIs and domain logic untouched.
- **Positive**: The mental model is consistent across Phenotype ecosystem crates, lowering onboarding friction for contributors.
- **Negative**: More files and directories than a flat structure. The separation is deliberate and offsets the cost through clarity.
- **Negative**: Requires discipline to keep `domain` free of `async` runtime details and transport-specific types; code reviews must enforce this boundary.
