# PRD — pyhex

## Overview
pyhex is a Python library implementing the Hexagonal Architecture (Ports and Adapters) pattern. It provides abstract port definitions, adapter base classes, use case protocols, and domain model primitives to enforce clean architecture boundaries in Python services and applications.

## Epics

### E1 — Core Port/Adapter Abstractions
**E1.1** `InboundPort` and `OutboundPort` abstract base classes using Python `Protocol` (structural subtyping).
**E1.2** `UseCase` base class with typed execute method and explicit error type via `Result`.
**E1.3** Adapter registry for port-to-adapter wiring at application startup.

### E2 — Domain Model Utilities
**E2.1** `Entity` base class with `id` field and identity-based equality.
**E2.2** `ValueObject` frozen dataclass base with structural equality.
**E2.3** `DomainEvent` dataclass with `occurred_at`, `correlation_id`, `causation_id`.
**E2.4** `Result[T, E]` type (Ok/Err) using Python generics for explicit error handling.

### E3 — Dependency Injection
**E3.1** Lightweight `HexContainer` supporting port-to-adapter binding.
**E3.2** Lazy adapter initialization.
**E3.3** Scoped containers for request-scoped adapters.

### E4 — Testing Utilities
**E4.1** In-memory adapter implementations: `InMemoryRepository`, `InMemoryEventBus`.
**E4.2** `PortSpy` wrapper that records all port invocations.
**E4.3** Pytest fixtures for wiring use cases with test adapters.

## Acceptance Criteria
- No dependencies beyond Python stdlib for core module; adapters for frameworks are separate extras.
- Full mypy strict mode compliance with no `type: ignore` suppression.
- Python 3.11+ minimum; leverages `Self` type, `tomllib`, PEP 695 where available.
