---
layout: home
title: Apisync - Universal API Toolkit
titleTemplate: false
---

# Apisync

Universal API toolkit with REST, GraphQL, and WebSocket support.

## Overview

`Apisync` is a Rust API toolkit providing REST, GraphQL, and WebSocket support
over a transport-agnostic domain core. It is the foundation library for
building Phenotype HTTP services: one domain model, three adapters
(hyper REST, async-graphql, tokio-tungstenite WebSocket), and a small set of
shipped endpoints for CRUD and health probes.

## Features

- **REST**: hyper 1.0 HTTP/1.1 server (`HyperServer`) with CRUD endpoints
- **GraphQL**: schema + resolver helpers over the same domain model
- **WebSocket**: connection management, framing, and broadcast hub
- **Middleware**: `RequestIdMiddleware` plus a composable chain model
- **Async-first**: built on tokio and hyper; all handlers are async

## Architecture

```
src/
├── domain/         # Core types + Endpoint trait (no I/O)
├── application/    # Router + Handler composition
├── adapters/       # rest/ graphql/ websocket transports
├── endpoints/      # ItemCrudEndpoint, Healthz/Readyz probes
└── infrastructure/ # tracing logging init
```

See [Architecture](./architecture) for the full hexagonal layout.

## Quick Start

```rust
use std::sync::Arc;
use apisync::adapters::rest::HyperServer;
use apisync::endpoints::ItemCrudEndpoint;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let endpoint = Arc::new(ItemCrudEndpoint::new());
    let server = HyperServer::new("127.0.0.1:8080".parse()?, endpoint).await?;
    server.run().await?;
    Ok(())
}
```

## Links

- [Repository](https://github.com/KooshaPari/Apisync)
- [Installation](./installation) · [Quick Start](./quickstart)
- [API Reference](./api) · [Architecture](./architecture)
- [User Journeys](./journeys/) · [User Stories](./stories/)
- [Traceability](./traceability/) · [ADRs](./adr/)
- [Research: State of the Art](./research/SOTA)
