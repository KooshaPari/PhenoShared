# ADR-004: API Design Principles

## Status

**Accepted** — 2026-05-25

## Author

KooshaPari

## Context

The Phenotype ecosystem exposes two distinct API surfaces: engine-side RPC calls between simulation/game-loop components where strict ordering and typed method dispatch matter, and web-facing REST endpoints consumed by dashboards and external integrators who expect discoverable, cacheable HTTP semantics. A single protocol cannot serve both surfaces optimally.

## Decision

We use **JSON-RPC 2.0** for all engine-to-engine and service-to-service calls (the internal transport layer), and **REST over HTTP/JSON** for all public-facing and web-dashboard APIs.

JSON-RPC provides a lightweight, protocol-neutral envelope for typed method dispatch. It maps naturally to Rust service traits, is trivially testable without HTTP infrastructure, and can run over WebSockets or stdio as well as HTTP. REST is the appropriate choice for web-facing APIs because browsers, CDN edge caches, and third-party clients all expect standard HTTP verbs and status codes; the constraint model also prevents RPC anti-patterns from leaking into the public surface.

## Consequences

### Positive
- Engine services communicate with zero REST overhead and full type safety
- Web APIs remain RESTful and discoverable via OpenAPI spec
- Clear boundary prevents RPC anti-patterns from reaching public consumers
- Both protocols are JSON-native, so serialisation logic is shared

### Negative / Trade-offs
- Two protocol stacks require developers to be fluent in both
- JSON-RPC error codes differ from HTTP status codes; mapping layer needed at the boundary
- GraphQL or gRPC may be reconsidered if subscription patterns become dominant

## References

- ADR-001 — Hexagonal Architecture (API adapters are primary ports)
- ADR-002 — Technology Stack (TypeScript TanStack for web client)

---

*Decision Date: 2026-05-25*
*Next Review: 2027-05-25*
