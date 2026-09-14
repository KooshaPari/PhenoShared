# apikit

Rust API toolkit providing REST, GraphQL, and WebSocket support. Foundation library for building Phenotype HTTP services.

## Stack
- Language: Rust
- Key deps: Cargo, axum (HTTP), async-graphql, tokio-tungstenite

## Structure
- `src/`: Rust library
  - `rest.rs`: REST router and handler abstractions
  - `graphql.rs`: GraphQL schema and resolver helpers
  - `ws.rs`: WebSocket connection management
  - `middleware.rs`: Auth, logging, CORS middleware

## Key Patterns
- Async-first (tokio); all handlers are async
- Type-safe routing and response types
- Middleware as composable tower layers
- Unified error type across REST/GraphQL/WS

## Adding New Functionality
- New REST endpoints: add route handlers in `src/rest.rs`
- New GraphQL types: extend schema in `src/graphql.rs`
- New middleware: add tower `Layer` impl in `src/middleware.rs`
- Run `cargo test` to verify
