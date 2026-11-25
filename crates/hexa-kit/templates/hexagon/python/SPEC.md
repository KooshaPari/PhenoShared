# HexaPy — Specification

Lightweight, dependency-free hexagonal architecture kit for Python applications.

## Architecture

```
┌───────────────────────────────────────────────┐
│             Adapters (Infrastructure)          │
│  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐ │
│  │ FastAPI│  │ gRPC  │  │  CLI  │  │  DB   │ │
│  └───┬───┘  └───┬───┘  └───┬───┘  └───┬───┘ │
└──────┼──────────┼──────────┼──────────┼──────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌───────────────────────────────────────────────┐
│                Ports (Interfaces)              │
│  ┌────────────┐         ┌────────────┐        │
│  │ InputPorts │         │ OutputPorts│        │
│  │ (driving)  │         │  (driven)  │        │
│  └────────────┘         └────────────┘        │
└───────────────────────────────────────────────┘
       │                        │
       ▼                        ▼
┌──────────────────┐  ┌────────────────────────┐
│   Domain Layer   │  │   Application Layer    │
│  Pure Python     │  │  UseCases, DTOs        │
│  0 external deps │  │  Commands, Queries     │
└──────────────────┘  └────────────────────────┘
```

## Components

| Module | Role | Key Types |
|--------|------|-----------|
| domain | Core building blocks | Entity, AggregateRoot, ValueObject, DomainEvent |
| ports | Interface contracts | InputPort, OutputPort, Repository, EventStore |
| application | Use case orchestration | UseCase, Command, Query |

## Data Models

```python
@dataclass(frozen=True)
class EntityId:
    value: str

    @classmethod
    def create(cls) -> "EntityId":
        return cls(value=str(uuid4()))

class Entity(ABC):
    def __init__(self, id: EntityId) -> None:
        self._id = id

    @property
    def id(self) -> EntityId:
        return self._id

class AggregateRoot(Entity):
    def __init__(self, id: EntityId) -> None:
        super().__init__(id)
        self._events: list[DomainEvent] = []

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

class ValueObject(ABC):
    @abstractmethod
    def __eq__(self, other: object) -> bool: ...

@dataclass(frozen=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=datetime.utcnow)
```

## API Design

```python
from pyhex.domain import Entity, AggregateRoot, EntityId, DomainEvent
from pyhex.ports import Repository, InputPort, OutputPort

class Order(AggregateRoot):
    def __init__(self, id: EntityId, customer_id: str):
        super().__init__(id)
        self.customer_id = customer_id
        self.status = "pending"

class OrderRepository(Repository[Order, EntityId], OutputPort):
    async def save(self, entity: Order) -> Order: ...
    async def find_by_id(self, id: EntityId) -> Order | None: ...

class CreateOrderUseCase(UseCase[CreateOrderInput, EntityId]):
    def __init__(self, repo: OrderRepository):
        self.repo = repo

    async def execute(self, input: CreateOrderInput) -> EntityId:
        order = Order(EntityId.create(), input.customer_id)
        await self.repo.save(order)
        return order.id
```

## Package Layout

```
pyhex/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entity.py
│   ├── value_object.py
│   ├── aggregate.py
│   └── event.py
├── ports/
│   ├── __init__.py
│   ├── input_port.py
│   ├── output_port.py
│   └── repository.py
└── application/
    ├── __init__.py
    ├── usecase.py
    ├── command.py
    └── query.py
```

## Performance Targets

| Metric | Target |
|--------|--------|
| Python version | 3.10+ |
| Zero runtime dependencies | domain module |
| Test suite | < 10s |
| mypy strict | 0 errors |
| Test coverage | > 90% |
| ruff | 0 warnings |

## Quality Gates

- `pytest` — all tests pass
- `mypy pyhex` — strict typing, 0 errors
- `ruff check pyhex` — 0 warnings
- `black --check pyhex` — formatted
- Domain module imports zero external packages
- Full async/await support on all I/O ports
