# PRD — ts-hex

## Overview
ts-hex is a TypeScript library implementing the Hexagonal Architecture (Ports and Adapters) pattern for the Phenotype ecosystem. It provides typed port interfaces, adapter base classes, and dependency injection utilities to enforce clean architecture boundaries in TypeScript applications and services.

## Epics

### E1 — Core Port/Adapter Abstractions
**E1.1** Define typed `Port<T>` and `Adapter<T>` generic interfaces.
**E1.2** Inbound port (driving) and outbound port (driven) distinctions with separate type markers.
**E1.3** Use case base class with typed input/output and error handling.

### E2 — Dependency Injection Container
**E2.1** Lightweight DI container for wiring ports to adapters without framework coupling.
**E2.2** Scope management: singleton, transient, and per-request scopes.
**E2.3** Lazy initialization for expensive adapters.

### E3 — Domain Model Utilities
**E3.1** `Entity<ID>` base class with identity equality.
**E3.2** `ValueObject` base class with structural equality.
**E3.3** `DomainEvent` base class with metadata (timestamp, correlation ID, causation ID).
**E3.4** `Result<T, E>` type for explicit error handling without exceptions.

### E4 — Testing Utilities
**E4.1** In-memory adapter stubs for common ports (repository, event bus, logger).
**E4.2** Port spy: records calls to a port for assertion in tests.
**E4.3** Use case test harness that wires stubs automatically.

## Acceptance Criteria
- No runtime dependencies beyond TypeScript stdlib; all framework integrations are opt-in peer deps.
- Port/adapter boundaries are enforced at compile time via TypeScript type system.
- All public APIs have JSDoc and type-level tests (tsd or expect-type).
