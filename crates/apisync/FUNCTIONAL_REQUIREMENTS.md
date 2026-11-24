# Functional Requirements — apikit

## FR-API-001
The library SHALL expose a `RestClient` struct with methods: `get`, `post`, `put`, `patch`, `delete`.

## FR-API-002
Each `RestClient` method SHALL accept a path `&str` and optional typed body `T: Serialize`, returning `Result<U: DeserializeOwned, ApiError>`.

## FR-API-003
HTTP 4xx responses SHALL produce `ApiError::Client { status, body }`.

## FR-API-004
HTTP 5xx responses SHALL produce `ApiError::Server { status, body }`.

## FR-API-005
Network/transport errors SHALL produce `ApiError::Transport(String)`.

## FR-GQL-001
The library SHALL expose a `GraphQlClient` struct with an `execute<Q: Serialize, R: DeserializeOwned>` method.

## FR-GQL-002
GraphQL `errors` array in response SHALL produce `ApiError::GraphQl(Vec<GraphQlError>)`.

## FR-WS-001
The library SHALL expose a `WsConnection` struct with `send(msg: WsMessage)` and `recv() -> Option<WsMessage>` async methods.

## FR-WS-002
WebSocket connection errors SHALL produce `ApiError::WebSocket(String)`.

## FR-OBS-001
All outbound HTTP requests SHALL emit a `tracing::info_span\!` with fields: `method`, `url`, `status`.

## FR-BUILD-001
The library SHALL compile with `edition = "2021"` or later.

## FR-BUILD-002
`cargo clippy -- -D warnings` SHALL exit 0.

## FR-TEST-001
`cargo test` SHALL exit 0.

## FR-TEST-002
HTTP-layer tests SHALL use HTTP mocking (mockito or wiremock) — no live network calls in tests.

## FR-DOC-001
All public structs, traits, and functions SHALL have doc comments (`///`).
