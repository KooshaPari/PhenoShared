# API Reference

This page documents the stable public surface of `apisync` (crate version 0.2).
All items below are re-exported from the crate root unless noted; the complete
list lives in `src/lib.rs`.

## Domain types (`apisync::domain`)

### `Request`

```rust
pub struct Request {
    pub path: String,
    pub method: String,
    pub headers: Vec<(String, String)>,
    pub body: Option<Vec<u8>>,
}
```

Builder methods: `Request::new(path, method)`, `.with_header(k, v)`, `.with_body(bytes)`.

### `Response`

```rust
pub struct Response {
    pub status: u16,
    pub headers: Vec<(String, String)>,
    pub body: Option<Vec<u8>>,
}
```

Constructors/helpers: `Response::new(status)`, `Response::ok()` (200),
`Response::not_found()` (404), `Response::server_error()` (500), and the
`.with_header` / `.with_body` builders.

### `Endpoint` trait

```rust
#[async_trait]
pub trait Endpoint: Send + Sync {
    async fn handle(&self, req: Request) -> Response;
}
```

Implemented for `Box<E>` and for the `Router`, so endpoints compose.

### Item model

- `Item { id: u64, name: String, description: String }`
- `CreateItem { name: String, description: String }`
- `UpdateItem { name: Option<String>, description: Option<String> }`
- `ItemStore` — thread-safe in-memory store: `new`, `list`, `get(id)`,
  `create(CreateItem)`, `update(id, UpdateItem)`, `delete(id)`.

## Endpoints (`apisync::endpoints`)

### `ItemCrudEndpoint`

REST CRUD over an `ItemStore`:

| Method | Path          | Success           | Errors         |
| ------ | ------------- | ----------------- | -------------- |
| GET    | `/items`      | 200 + `Vec<Item>` | —              |
| GET    | `/items/{id}` | 200 + `Item`      | 404            |
| POST   | `/items`      | 201 + `Item`      | 400 (bad JSON) |
| PUT    | `/items/{id}` | 200 + `Item`      | 400, 404       |
| DELETE | `/items/{id}` | 200               | 400, 404       |

`ItemCrudEndpoint::new()` starts with an empty store.

### Probes

- `HealthzEndpoint` — `GET /healthz` → 200 (liveness).
- `ReadyzEndpoint` — `GET /readyz` → 200 (readiness; cheap, dependency-free
  by default so downstream services can wrap it with their own checks).

## REST adapter (`apisync::adapters::rest`)

### `HyperServer`

```rust
pub struct HyperServer { /* … */ }

impl HyperServer {
    pub async fn new(
        addr: SocketAddr,
        endpoint: Arc<dyn Endpoint>,
    ) -> Result<Self, Box<dyn std::error::Error + Send + Sync>>;
    pub fn with_body_limit(mut self, limit: usize) -> Self; // default 1 MiB
    pub fn body_limit(&self) -> usize;
    pub fn local_addr(&self) -> Result<SocketAddr, …>;
    pub async fn run(self) -> Result<(), …>;
}
```

`MAX_REQUEST_BODY_BYTES` (1 MiB) caps request-body buffering.

## GraphQL adapter (`apisync::adapters::graphql`)

- `build_schema(store: Arc<ItemStore>) -> GraphQLSchema` — constructs the
  schema with `QueryRoot`, `MutationRoot`, and `SubscriptionRoot`.
- `GraphQLEndpoint::new(schema)` / `GraphQLEndpoint::with_store(store)` —
  mounts GraphQL on the domain `Router`.
- `GraphItem` — the GraphQL representation of `Item`.

Example:

```rust
use std::sync::Arc;
use apisync::adapters::graphql::GraphQLEndpoint;
use apisync::domain::ItemStore;

let endpoint = GraphQLEndpoint::with_store(Arc::new(ItemStore::new()));
```

## WebSocket adapter (`apisync::adapters::websocket`)

- `WebSocketServer` — accepts connections, manages them via a broadcast hub,
  and exchanges framed JSON `WsMessage`s.
- `WebSocketEndpoint` — mounts the WebSocket service on the domain `Router`.
- `BroadcastHub` — fans out `ItemCreated` / `ItemUpdated` / `ItemDeleted`
  events to subscribed topics.
- `WsMessage` — tagged enum (`type` field, snake_case): `subscribe`,
  `unsubscribe`, `item_created`, `item_updated`, `item_deleted`, `get_items`,
  `create_item`, `update_item`, …

## Application layer (`apisync::application`)

- `Router::new()` / `Router::route(path, endpoint)` / `Router::handle(&Request)`
  — exact-path dispatch, 404 for unknown paths. Implements `Endpoint`.
- `Handler` — synchronous `fn handle(&self, Request) -> Response` trait.

## Middleware (`apisync::domain::middleware`)

- `Middleware<F>` + `Next<F>` — the chain model (see Architecture).
- `RequestIdMiddleware` — echoes inbound `X-Request-Id` or generates a fresh
  id, and stamps it on the response.

## Logging (`apisync::infrastructure::logging`)

- `logging::init()` — installs a `tracing_subscriber` with an env-filter
  defaulting to `info` (`RUST_LOG` overrides). Safe to call more than once.

## Crate root

- `ApiKit::new()` / `ApiKit::default()` — top-level handle placeholder for
  configured instances (the crate ships self-contained endpoints today).
- The root prelude re-exports `Router`, `Handler`, `HyperServer`,
  `GraphQLSchema`, `WebSocketServer`, `WsMessage`, `Middleware`, `Next`,
  `RequestIdMiddleware`, the item model, and all three endpoints.
