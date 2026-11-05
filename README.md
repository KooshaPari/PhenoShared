# Phenotype architecture: public overview

This sanitized, history-free snapshot summarizes selected high-level architecture concepts. It omits internal inventory, identities, credentials, host paths, session records and operational details. It does not reproduce the full local architecture document or claim that every concept is implemented.

## Mental model

A multi-agent system benefits from separating the surfaces where people interact, the coordination of work, the execution of tasks and the storage of durable state. Each surface should have a clearly defined responsibility rather than silently becoming an authority over the others.

## Cross-cutting design principles

- Assign an explicit owner and authority boundary to each component.
- Use stable identifiers and documented contracts between components.
- Separate observations from desired or planned behavior.
- Preserve provenance and avoid treating a presentation surface as the underlying source of truth.
- Require explicit authorization for sensitive operations and use least-privilege access.
- Design for recovery, idempotency and auditability across handoffs.
- Validate the complete user-visible workflow, not just component health checks.

The full original document, including its local uncommitted changes and prior history, remains local and is excluded from this public branch.
