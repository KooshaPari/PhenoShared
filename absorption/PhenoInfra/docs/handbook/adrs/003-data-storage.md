# ADR-003: Data Storage Strategy

## Status

**Accepted** — 2026-05-25

## Author

KooshaPari

## Context

Phenotype-ecosystem services need durable relational storage, a low-latency cache/pub-sub layer, a message bus for event-driven workflows, and object storage for blobs and artifacts. We evaluated several combinations and settled on a stack that maps one tool per responsibility, avoiding overlap and minimising operational complexity.

## Decision

We adopt a four-tier storage stack:

| Tier | Technology | Role |
|------|-----------|------|
| Relational | **PostgreSQL** | Source of truth for all structured, transactional data |
| Cache / KV | **DragonFly** | Redis-compatible in-memory layer; replaces Redis with better multi-core throughput |
| Messaging | **NATS JetStream** | Durable, at-least-once event streaming and work queues |
| Object | **MinIO** | S3-compatible blob store for artifacts, models, and media |

PostgreSQL is the battle-tested default for ACID transactional data; its JSON/JSONB support also covers semi-structured payloads without requiring a separate document store. DragonFly's Redis-wire compatibility allows drop-in migration from Redis while delivering 25× higher throughput on multi-core hardware. NATS JetStream covers ordered, durable messaging without the operational weight of Kafka; it integrates natively with the Phenotype service mesh. MinIO provides an S3-compatible API deployable on-premise or in CI, eliminating cloud-only object-storage lock-in.

## Consequences

### Positive
- Each tier has a clear, non-overlapping responsibility
- DragonFly is Redis-API compatible — no client code changes
- NATS embeds into services as a library, simplifying local dev
- MinIO runs in Docker for local and CI parity with production

### Negative / Trade-offs
- Four distinct technologies increases operator knowledge requirements
- NATS JetStream semantics differ from Kafka; team needs onboarding
- DragonFly is newer than Redis; long-term support track less proven

## References

- ADR-001 — Hexagonal Architecture (storage adapters are secondary ports)
- [Civis infra stack notes](../MEMORY/project_civis_infra_stack.md)

---

*Decision Date: 2026-05-25*
*Next Review: 2027-05-25*
