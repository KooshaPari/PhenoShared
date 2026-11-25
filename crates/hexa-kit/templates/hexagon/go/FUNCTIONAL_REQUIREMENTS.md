# FUNCTIONAL_REQUIREMENTS — go-hex

## FR-PORT-001: Port Interfaces
**SHALL** define `InboundPort` and `OutboundPort` as empty marker interfaces for type documentation.
Traces to: E1.1

## FR-PORT-002: Use Case Type
**SHALL** define `UseCaseFunc[TIn, TOut any]` as `func(ctx context.Context, input TIn) (TOut, error)`.
Traces to: E1.2

## FR-DOMAIN-001: Entity
**SHALL** export `Entity[ID comparable]` struct with `ID` field; `Equal(other Entity[ID]) bool` method.
Traces to: E2.1

## FR-DOMAIN-002: Value Object
**SHALL** export `ValueObject` interface with `Equals(other ValueObject) bool`.
Traces to: E2.2

## FR-DOMAIN-003: Domain Event
**SHALL** export `DomainEvent` struct with `OccurredAt time.Time`, `CorrelationID string`, `CausationID string`.
Traces to: E2.3

## FR-DOMAIN-004: Result Type
**SHALL** export `Result[T any]` with `NewOk[T](v T) Result[T]` and `NewErr[T](err error) Result[T]`; `Unwrap() (T, error)`.
Traces to: E2.4

## FR-DI-001: Container
**SHALL** provide `Container` with `Bind[T any](impl T)` and `Resolve[T any]() (T, error)` using generics.
Traces to: E3.1

## FR-TEST-001: In-Memory Repository
**SHALL** provide `InMemoryRepository[T any, ID comparable]` implementing standard CRUD repository interface.
Traces to: E4.1

## FR-TEST-002: Event Capture
**SHALL** provide `EventCapture` with `Captured() []DomainEvent` and `AssertPublished(t, eventType)`.
Traces to: E4.2
