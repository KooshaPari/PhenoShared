# ADR-002: Choice of hyper over axum for REST

## Status

Accepted

## Context

Apisync needs a robust HTTP/1.1 and HTTP/2 server and client foundation for its REST adapter. The Rust ecosystem offers several mature options, ranging from high-level frameworks to low-level libraries. We evaluated candidates based on control granularity, ecosystem compatibility, compile-time overhead, and alignment with a toolkit (rather than a full framework) philosophy.

Alternatives considered:
- **axum**: Ergonomic, tower-based middleware, and widely used in production. However, it imposes its own routing and extract abstractions, which would leak into the domain layer if we are not careful.
- **reqwest**: Excellent for client-only use cases, but it is a higher-level wrapper around hyper and offers less control over connection pooling, HTTP/2 settings, and raw body streaming.
- **actix-web**: Mature and fast, but uses a different runtime model (actix-rt) and brings in a larger dependency tree that is harder to align with the tokio-first ecosystem we standardize on.
- **rocket**: Requires nightly and is opinionated about routing, forms, and templating—too heavy for a transport-agnostic toolkit.

## Decision

Use **hyper 1.x** directly as the HTTP transport layer for the REST adapter.

- We own the service function and request/response mapping, which keeps domain logic decoupled from routing frameworks.
- Hyper 1.x provides full control over HTTP/1.1 and HTTP/2 semantics, connection management, and body streaming.
- Higher-level convenience (e.g., a simple client) can be re-exported as optional features in the future without breaking the core abstraction.

## Consequences

- **Positive**: Maximum control over HTTP semantics; no hidden middleware or routing magic that could surprise consumers.
- **Positive**: Minimal dependency tree at the core layer. `hyper-util` and `http-body-util` provide the minimal tokio glue we need.
- **Positive**: Because we map hyper requests to our domain `Request` type internally, swapping hyper for another transport later is confined to `src/adapters/rest/`.
- **Negative**: More boilerplate for common patterns (routing, header extraction, JSON deserialization). We mitigate this by providing thin helpers in `adapters/rest/` without exposing them as public API contracts.
- **Negative**: Contributors must understand hyper’s service-fn and `Incoming` body model, which is lower-level than axum’s handler signatures.
