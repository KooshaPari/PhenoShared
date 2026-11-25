# Architecture Decision Records

Apisync records significant architecture decisions as ADRs. The canonical
source is `docs/adr/` (see the header note in the root `ADR.md`).

| ADR                                                          | Decision                              |
| ------------------------------------------------------------ | ------------------------------------- |
| [001 — Hexagonal architecture](./001-hexagonal-architecture) | Domain core with transport adapters   |
| [002 — Hyper over axum](./002-hyper-over-axum)               | hyper 1.0 as the HTTP transport       |
| [003 — async-graphql](./003-async-graphql)                   | async-graphql for the GraphQL adapter |
| [004 — tokio-tungstenite](./004-tokio-tungstenite)           | WebSocket connection management       |
| [005 — criterion](./005-criterion)                           | Criterion for benchmarks              |
