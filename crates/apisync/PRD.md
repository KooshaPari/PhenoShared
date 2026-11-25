# Product Requirements Document — apikit

## Overview

`apikit` is a Rust library providing a unified API toolkit with support for REST, GraphQL, and WebSocket protocols. It wraps `hyper` for HTTP transport and provides higher-level abstractions for building API clients and servers in Phenotype ecosystem services.

## Problem Statement

Phenotype Rust services repeatedly implement the same HTTP/API boilerplate — request serialisation, error mapping, response parsing, and retry logic. `apikit` centralises this so all services share a single, well-tested implementation.

## Goals

- Provide ergonomic Rust abstractions for REST, GraphQL, and WebSocket APIs.
- Wrap `hyper` 1.x for HTTP transport; expose a higher-level client and server interface.
- Support async/await with Tokio runtime.
- Expose a hexagonal ports-and-adapters internal layout so the library itself is modular.
- Publish to crates.io as `apikit`.

## Non-Goals

- Not a full application framework (not replacing Axum or Actix).
- Does not handle authentication — that is the responsibility of `cryptokit`.
- Does not provide database access — that is `dbkit`.

## Epics & User Stories

### E1 — REST Client
- E1.1: As a developer, I can create a typed REST client with `ApiKit::new(base_url)`.
- E1.2: GET, POST, PUT, PATCH, DELETE methods accept typed request bodies and return typed responses.
- E1.3: 4xx/5xx responses map to `ApiError` variants with status code and body.

### E2 — REST Server Utilities
- E2.1: Request parsing helpers extract typed bodies from `hyper::Request`.
- E2.2: Response builders produce `hyper::Response` from typed Rust values.

### E3 — GraphQL Support
- E3.1: GraphQL query execution wraps HTTP transport with query/variable serialisation.
- E3.2: GraphQL errors are mapped to typed `GraphQlError` variants.

### E4 — WebSocket Support
- E4.1: WebSocket connection management wraps `tokio-tungstenite`.
- E4.2: Message send/receive are async and typed (text, binary, ping/pong).

### E5 — Observability
- E5.1: All outbound requests emit `tracing` spans with method, URL, and status.
- E5.2: Errors include correlation IDs for log correlation.

### E6 — Testing
- E6.1: `cargo test` passes with zero failures.
- E6.2: Integration tests use `mockito` or `wiremock` for HTTP mocking.

## Acceptance Criteria

- `cargo build` and `cargo test` succeed with zero warnings.
- `cargo clippy -- -D warnings` exits 0.
- All public API functions have doc comments with examples.
