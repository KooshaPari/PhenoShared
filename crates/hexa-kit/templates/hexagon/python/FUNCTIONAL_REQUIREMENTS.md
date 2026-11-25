# FUNCTIONAL_REQUIREMENTS — pyhex

## FR-PORT-001: Protocol-Based Ports
**SHALL** define `InboundPort` and `OutboundPort` as `Protocol` classes (PEP 544) for structural subtyping.
Traces to: E1.1

## FR-PORT-002: Use Case Base
**SHALL** provide `UseCase[TInput, TOutput, TError]` abstract class with `execute(input: TInput) -> Result[TOutput, TError]`.
Traces to: E1.2

## FR-DOMAIN-001: Entity
**SHALL** export `Entity[ID]` dataclass base; `__eq__` and `__hash__` based on `id` field only.
Traces to: E2.1

## FR-DOMAIN-002: Value Object
**SHALL** export `ValueObject` frozen dataclass base; equality based on all fields via `__eq__`.
Traces to: E2.2

## FR-DOMAIN-003: Domain Event
**SHALL** export `DomainEvent` dataclass with `occurred_at: datetime`, `correlation_id: str`, `causation_id: str`.
Traces to: E2.3

## FR-DOMAIN-004: Result Type
**SHALL** export `Result[T, E]` with `Ok[T]` and `Err[E]`; support `map`, `flat_map`, `map_err`, `unwrap_or`.
Traces to: E2.4

## FR-DI-001: Container
**SHALL** provide `HexContainer` with `bind(port, adapter)` and `resolve(port)` methods.
Traces to: E3.1

## FR-TEST-001: In-Memory Stubs
**SHALL** provide `InMemoryRepository[T, ID]` and `InMemoryEventBus` implementations.
Traces to: E4.1

## FR-TEST-002: Port Spy
**SHALL** provide `PortSpy[T]` that wraps a port and records calls with args and return values.
Traces to: E4.2

## FR-TEST-003: Pytest Fixtures
**SHALL** provide `pytest` plugin with `hex_container` fixture for test use case wiring.
Traces to: E4.3
