# ADR-001: Hexagonal Architecture Design Decisions

**Status**: Accepted  
**Date**: 2026-03-25  
**Deciders**: Phenotype Architecture Team

## Context

go-hex is a hexagonal architecture toolkit for Go that provides a foundation for building maintainable, testable applications following Clean Architecture principles.

## Decision Drivers

- Need for consistent architecture across Phenotype Go projects
- Support for domain-driven design patterns
- Testability requirements (TDD/BDD)
- Clear separation between domain logic and infrastructure
- Type safety and compile-time checks

## Decisions

### 1. Package Structure

**Decision**: Four-layer hexagonal structure:
- `domain/` - Pure business logic, no external dependencies
- `application/` - Use cases, DTOs, handlers
- `ports/` - Interface definitions (InputPort, OutputPort)
- `infrastructure/` - Adapters (REST, persistence, messaging)

**Rationale**: Follows Clean Architecture principles with dependency inversion pointing toward the domain layer.

### 2. Entity ID Type

**Decision**: Use `uuid.UUID` as `EntityID`

```go
type EntityID = uuid.UUID
```

**Rationale**: 
- UUIDs provide natural key strategy for distributed systems
- No database round-trip needed for ID generation
- Good performance with database indexes

### 3. Value Objects

**Decision**: Value objects implement `ValueObject` interface with `Equals()` and `String()` methods

```go
type ValueObject interface {
    Equals(ValueObject) bool
    String() string
}
```

**Rationale**:
- Immutable by design
- Compared by value, not identity
- Enables domain modeling with strong types (Email, Money, etc.)

### 4. Domain Events

**Decision**: Events implement `DomainEvent` interface for event sourcing

```go
type DomainEvent interface {
    EventType() string
    OccurredAt() Time
    AggregateID() EntityID
}
```

**Rationale**:
- Enables event sourcing and CQRS patterns
- Time wrapped to prevent infrastructure leakage
- Supports eventual consistency

### 5. Ports (Interfaces)

**Decision**: Marker interfaces for port classification

```go
type InputPort interface { isInputPort() }
type OutputPort interface { isOutputPort() }
```

**Rationale**:
- Clear separation of driving vs driven ports
- Enables dependency injection
- Framework-agnostic

### 6. Repository Pattern

**Decision**: Generic Repository interface with CRUD operations

```go
type Repository[T any] interface {
    Save(ctx context.Context, entity T) (T, error)
    FindByID(ctx context.Context, id string) (T, error)
    Delete(ctx context.Context, id string) error
    FindAll(ctx context.Context) ([]T, error)
}
```

**Rationale**:
- Type-safe with generics
- Supports various persistence backends
- Enables mock testing

### 7. Use Case Pattern

**Decision**: Function-based use cases with generic types

```go
type UseCase[I, O any] interface {
    Execute(ctx context.Context, input I) (O, error)
}
```

**Rationale**:
- Flexible for commands and queries (CQRS)
- Function adapters enable simple implementations
- Clear input/output contracts

### 8. Error Handling

**Decision**: Domain errors with error codes, application errors wrapping domain errors

```go
type DomainError struct {
    Code    string
    Message string
    Err     error
}
```

**Rationale**:
- Structured errors for better logging
- Error codes enable client handling
- Error wrapping preserves context

## xDD Methodologies Applied

| Category | Methodologies |
|----------|---------------|
| Development | TDD, BDD, DDD, ATDD, SDD |
| Design | SOLID, DRY, KISS, GRASP, SoC |
| Architecture | Clean, Hexagonal, Ports & Adapters, CQRS, EDA |
| Quality | Unit Testing, Property-Based Testing |
| Process | CI/CD, Code Review |

## Consequences

### Positive
- Clear separation of concerns
- High testability
- Easy to swap infrastructure implementations
- Supports event-driven architectures

### Negative
- More boilerplate for simple applications
- Learning curve for team members new to hexagonal architecture
- Additional abstraction layers may impact performance

## References

- [Hexagonal Architecture by Alistair Cockburn](https://alistair.cockburn.us/hexagonal-architecture/)
- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design by Eric Evans](https://www.domainlanguage.com/ddd/)
