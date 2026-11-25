# FUNCTIONAL_REQUIREMENTS — ts-hex

## FR-PORT-001: Port Interface
**SHALL** export `InboundPort<TInput, TOutput>` and `OutboundPort<TContract>` generic interfaces.
Traces to: E1.1, E1.2

## FR-PORT-002: Use Case Base
**SHALL** export `UseCase<TInput, TOutput, TError>` abstract class with `execute(input: TInput): Promise<Result<TOutput, TError>>`.
Traces to: E1.3

## FR-DI-001: Container
**SHALL** provide a `HexContainer` class with `register`, `resolve`, and `build` methods.
Traces to: E2.1

## FR-DI-002: Scopes
**SHALL** support `singleton`, `transient`, and `request` scopes on registered adapters.
Traces to: E2.2

## FR-DOMAIN-001: Entity
**SHALL** export `Entity<ID>` base class where equality is defined by `id` field only.
Traces to: E3.1

## FR-DOMAIN-002: Value Object
**SHALL** export `ValueObject<T>` base class where equality is deep structural comparison of all fields.
Traces to: E3.2

## FR-DOMAIN-003: Domain Event
**SHALL** export `DomainEvent` base class with `occurredAt: Date`, `correlationId: string`, `causationId: string`.
Traces to: E3.3

## FR-DOMAIN-004: Result Type
**SHALL** export `Result<T, E>` with `Ok<T>` and `Err<E>` variants and `map`, `flatMap`, `mapErr` combinators.
Traces to: E3.4

## FR-TEST-001: In-Memory Stubs
**SHALL** provide `InMemoryRepository<T, ID>`, `InMemoryEventBus`, and `NoOpLogger` adapter stubs.
Traces to: E4.1

## FR-TEST-002: Port Spy
**SHALL** provide `PortSpy<T>` that wraps any port and records all calls with arguments and return values.
Traces to: E4.2
