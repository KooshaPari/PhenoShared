# PRD — go-hex

## Overview
go-hex is a Go library implementing the Hexagonal Architecture (Ports and Adapters) pattern. It provides interface definitions, base types, dependency injection utilities, and domain model primitives to enforce clean architecture boundaries in Go services.

## Epics

### E1 — Core Port/Adapter Abstractions
**E1.1** Define `InboundPort` and `OutboundPort` marker interfaces for typed port declarations.
**E1.2** `UseCase[TInput, TOutput]` generic function type with standardized error return.
**E1.3** Adapter registry mapping port interfaces to concrete implementations.

### E2 — Domain Model Utilities
**E2.1** `Entity[ID comparable]` struct with identity-based `Equal` method.
**E2.2** `ValueObject` interface with `Equals(other ValueObject) bool`.
**E2.3** `DomainEvent` struct with `OccurredAt`, `CorrelationID`, `CausationID`.
**E2.4** `Result[T any]` type with `Ok` and `Err` variants using Go generics (1.21+).

### E3 — Dependency Injection
**E3.1** `Container` struct with `Bind` and `Resolve` methods using Go generics.
**E3.2** Singleton and transient registration modes.
**E3.3** Wire-compatible: adapters can be used with Google Wire code generation.

### E4 — Testing Utilities
**E4.1** `InMemoryRepository[T Entity[ID], ID comparable]` generic implementation.
**E4.2** `EventCapture` for capturing and asserting on domain events in tests.
**E4.3** `PortMock[T]` for recording calls to port methods.

## Acceptance Criteria
- Requires Go 1.21+ for generics support.
- Zero external dependencies in core module.
- All types are compatible with `go vet` and `staticcheck`.
- Full test coverage with testify assertions.
