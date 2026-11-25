# PyHex: Hexagonal Architecture Kit for Python

A lightweight, dependency-free hexagonal architecture kit for Python applications.

## Philosophy

PyHex provides the structural patterns for building applications with **Hexagonal Architecture** (Ports & Adapters) while respecting Python's idioms and simplicity.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Adapters Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   REST   │  │   gRPC   │  │    CLI   │            │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
└────────┼─────────────┼─────────────┼──────────────────┘
         │             │             │
         ▼             ▼             ▼
┌─────────────────────────────────────────────────────────┐
│                       Ports Layer                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  Input   │  │  Output  │  │  Domain  │            │
│  │  Ports   │  │  Ports   │  │  Events  │            │
│  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────┘
         │             │             │
         ▼             ▼             ▼
┌─────────────────────────────────────────────────────────┐
│                      Domain Layer                       │
│  Pure business logic - ZERO external dependencies       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Entities │  │ValueObjs │  │Aggregates│            │
│  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────┘
         │             │             │
         ▼             ▼             ▼
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ UseCases │  │   DTOs   │  │ Handlers │            │
│  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install pyhex
```

## Quick Start

```python
from pyhex.domain import Entity, AggregateRoot, EntityId, DomainEvent
from pyhex.ports import Repository, UseCase

# 1. Define your domain entity
class Order(AggregateRoot[EntityId]):
    def __init__(self, id: EntityId, customer_id: str):
        super().__init__(id)
        self.customer_id = customer_id
        self.status = "pending"

# 2. Define your repository port
class OrderRepository(Repository[Order, EntityId], OutputPort):
    async def save(self, entity: Order) -> Order:
        ...

    async def find_by_id(self, id: EntityId) -> Order | None:
        ...

# 3. Define your use case
class CreateOrderUseCase(UseCase[CreateOrderInput, OrderId]):
    def __init__(self, repo: OrderRepository):
        self.repo = repo

    async def execute(self, input: CreateOrderInput) -> OrderId:
        order = Order(EntityId.create(), input.customer_id)
        await self.repo.save(order)
        return order.id
```

## Core Patterns

### Domain Layer

- **Entity**: Objects with identity
- **ValueObject**: Immutable objects compared by value
- **AggregateRoot**: Cluster of domain objects treated as one unit
- **DomainEvent**: Something happened that's significant to the business
- **DomainService**: Operation that doesn't belong to an entity

### Ports Layer

- **InputPort**: Interface used by adapters to trigger use cases
- **OutputPort**: Interface implemented by infrastructure for external concerns
- **Repository**: Interface for entity persistence
- **EventStore**: Interface for event sourcing
- **MessageBus**: Interface for publishing events

### Application Layer

- **UseCase**: Single unit of application logic
- **Command/Query separation**: Clean separation of write and read operations

## Testing

```bash
pytest
pytest --cov=pyhex
mypy pyhex
black --check pyhex
```

## Best Practices

| Principle | Implementation |
|-----------|----------------|
| **SOLID** | DIP via ports, SRP via layers |
| **DRY** | Shared port interfaces |
| **KISS** | Simple interfaces, clear names |
| **GRASP** | Application Service pattern |
| **PoLA** | Descriptive error types |

## Comparison with Alternatives

| Feature | pyhex | fastapi | pyramid |
|---------|-------|--------|---------|
| Hexagonal-first | ✅ | ❌ | ❌ |
| Zero deps in domain | ✅ | ❌ | ❌ |
| Generic ports | ✅ | ❌ | ❌ |
| Event sourcing | ✅ | ❌ | ❌ |
| Async support | ✅ | ✅ | ✅ |

## License

MIT
