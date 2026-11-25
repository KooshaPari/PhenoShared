# Architecture

Apisync follows a hexagonal (ports & adapters) layout: the **domain** is pure
and transport-agnostic, **application** wiring composes endpoints, and
**adapters** translate between the domain types and concrete transports.

```
src/
├── lib.rs                # Crate root + stable public prelude (ApiKit handle)
├── domain/               # Core types and traits (no I/O)
│   ├── mod.rs            #   Request, Response, Endpoint, Item, ItemStore, ...
│   └── middleware.rs     #   Middleware, Next, RequestIdMiddleware
├── application/          # Composition layer
│   ├── router.rs         #   Router: path -> Endpoint dispatch
│   └── handler.rs        #   Handler trait for synchronous handlers
├── adapters/             # Transport adapters (ports)
│   ├── rest/             #   hyper 1.0 HTTP/1.1 server (HyperServer)
│   ├── graphql/          #   async-graphql schema + GraphQLEndpoint
│   └── websocket/        #   tokio-tungstenite server + broadcast hub
├── endpoints/            # Shipped endpoint implementations
│   └── mod.rs            #   ItemCrudEndpoint, HealthzEndpoint, ReadyzEndpoint
└── infrastructure/       # Cross-cutting concerns
    └── logging.rs        #   tracing subscriber init
```

## Domain layer (`domain`)

The heart of the library. `Request` and `Response` are plain serializable
structs with builder methods (`with_header`, `with_body`). The `Endpoint`
trait is the seam every adapter and router speaks:

```rust
#[async_trait]
pub trait Endpoint: Send + Sync {
    async fn handle(&self, req: Request) -> Response;
}
```

`Item` / `CreateItem` / `UpdateItem` and the thread-safe in-memory `ItemStore`
are the reference domain model used by all shipped adapters.

Middleware follows a chain model: `Middleware<F>` implementations wrap a
`Next<F>` handler and can transform the request before dispatch and the
response afterwards. `RequestIdMiddleware` echoes or generates an
`X-Request-Id` header on every response.

## Application layer (`application`)

`Router` maps exact request paths to `Arc<dyn Endpoint>` and returns
`404 Not Found` for unknown paths. It implements `Endpoint` itself, so a
router can be nested inside another router or mounted on a `HyperServer`.

## Adapter layer (`adapters`)

- **REST** — `HyperServer::new(addr, endpoint)` binds a TCP listener and
  serves HTTP/1.1 over hyper 1.0, translating between hyper and domain types.
  Request bodies are limited to 1 MiB by default to prevent unbounded
  buffering.
- **GraphQL** — `build_schema(store)` produces an async-graphql schema;
  `GraphQLEndpoint` mounts it on the domain `Router` so GraphQL and REST can
  share one dispatch path.
- **WebSocket** — `WebSocketServer` accepts connections and frames typed
  `WsMessage`s (subscribe/unsubscribe, item events, CRUD verbs) over
  tokio-tungstenite; `BroadcastHub` fans out item events to subscribers.

## Endpoints (`endpoints`)

`ItemCrudEndpoint` implements the full REST CRUD contract over `ItemStore`
(see the [API Reference](./api) for the route table). `HealthzEndpoint` and
`ReadyzEndpoint` answer liveness/readiness probes.

## Dependencies and rationale

The transport adapters depend on hyper 1.0 / async-graphql /
tokio-tungstenite; the domain layer depends only on `async-trait`, `serde`,
and `parking_lot`. Keeping the domain dependency-free of transports is what
lets a service swap REST for GraphQL or WebSocket without touching its
business logic. See the [ADRs](./adr/) for the individual decisions.
