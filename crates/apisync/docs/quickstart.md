# Quick Start

This guide boots a real HTTP/1.1 server on localhost serving the built-in
`ItemCrudEndpoint` (REST CRUD over an in-memory store).

## 1. Add the dependency

```bash
cargo add apisync tokio --features tokio/rt-multi-thread
```

## 2. Start the server

```rust
use std::sync::Arc;

use apisync::adapters::rest::HyperServer;
use apisync::endpoints::ItemCrudEndpoint;
use apisync::infrastructure::logging;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    logging::init();

    let endpoint = Arc::new(ItemCrudEndpoint::new());
    let server = HyperServer::new("127.0.0.1:8080".parse()?, endpoint).await?;

    println!("listening on http://127.0.0.1:8080");
    server.run().await?;
    Ok(())
}
```

The `HyperServer` adapter converts hyper requests into the domain `Request`
type, dispatches them to the endpoint, and translates the domain `Response`
back into an HTTP response. Request bodies are capped at 1 MiB by default
(`MAX_REQUEST_BODY_BYTES`).

## 3. Exercise the API

```bash
# List items (empty on a fresh store)
curl http://127.0.0.1:8080/items

# Create an item
curl -X POST http://127.0.0.1:8080/items \
  -H 'Content-Type: application/json' \
  -d '{"name":"first","description":"hello apisync"}'
# -> {"id":1,"name":"first","description":"hello apisync"}

# Fetch it back
curl http://127.0.0.1:8080/items/1

# Update it
curl -X PUT http://127.0.0.1:8080/items/1 \
  -H 'Content-Type: application/json' \
  -d '{"description":"updated"}'

# Delete it
curl -X DELETE http://127.0.0.1:8080/items/1

# Liveness / readiness probes
curl http://127.0.0.1:8080/healthz   # -> 200
curl http://127.0.0.1:8080/readyz    # -> 200
```

## Mounting your own endpoints

Any type implementing the [`Endpoint`](../api) trait (an `async fn handle(Request) -> Response`)
can be served the same way, either directly by `HyperServer` or through the
`Router`:

```rust
use apisync::application::Router;
use apisync::domain::{Request, Response};
use apisync::endpoints::{HealthzEndpoint, ItemCrudEndpoint};

let mut router = Router::new();
router.route("/items", ItemCrudEndpoint::new());
router.route("/healthz", HealthzEndpoint);
router.route("/readyz", ReadyzEndpoint);
// then: HyperServer::new(addr, Arc::new(router))
```

## GraphQL and WebSocket

The same domain model is exposed over GraphQL (`build_schema` +
`GraphQLEndpoint`) and WebSocket (`WebSocketServer` / `WebSocketEndpoint`).
See the [API Reference](./api) for examples.

## Next steps

- [API Reference](./api) — every public type and adapter
- [Architecture](./architecture) — the hexagonal layout
- [User Journeys](./journeys/) and [User Stories](./stories/) — workflow walkthroughs
