# ADR-003: Choice of async-graphql for GraphQL

## Status

Accepted

## Context

The GraphQL adapter in Apisync must expose a typed schema, support queries, mutations, and subscriptions, and integrate cleanly with the tokio runtime. We need a library that is actively maintained, has strong async support, and does not force us to adopt a particular web framework to serve the endpoint.

Alternatives considered:
- **juniper**: Mature and schema-first, but its async ecosystem integration is less polished than async-graphql, and subscription support historically required more boilerplate.
- **graphql-ws / async-graphql-ws**: These are protocol crates, not full schema engines. We would still need a schema definition layer on top.
- **cynic**: Excellent for client-side GraphQL in Rust, but it is not a server-side schema engine.

## Decision

Use **async-graphql 7.x** as the GraphQL engine for the GraphQL adapter.

- It provides a code-first schema definition with derive macros, keeping the schema close to the Rust types.
- Native async/await support and built-in integration with tokio and futures.
- Subscription support is first-class and does not require a separate protocol crate.
- We can serve the schema over any HTTP transport (hyper, axum, warp, etc.) because async-graphql decouples the schema from the server layer.

## Consequences

- **Positive**: Rapid schema development with compile-time type safety. Macros reduce boilerplate without sacrificing control.
- **Positive**: The schema object can be unit-tested independently of the HTTP server, aligning with the hexagonal boundary between `adapters/graphql/` and `domain/`.
- **Positive**: Strong ecosystem momentum and active maintenance reduce long-term risk.
- **Negative**: Procedural macros increase compile times slightly. This is a standard trade-off in Rust and is acceptable for a toolkit crate.
- **Negative**: The API surface of async-graphql is large. We must guard against leaking its types into `domain/` by mapping to transport-agnostic types at the adapter boundary.
