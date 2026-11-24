# TsHex: Hexagonal Architecture Kit for TypeScript

A lightweight, dependency-free hexagonal architecture kit for TypeScript/JavaScript applications.

## Philosophy

TsHex provides the structural patterns for building applications with **Hexagonal Architecture** (Ports & Adapters) while respecting TypeScript's types and JavaScript's flexibility.

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
npm install @phenotype-dev/ts-hex
```

## Quick Start

```typescript
import { 
  BaseEntity, 
  Uuid, 
  BaseAggregate,
  BaseDomainEvent,
  type EntityId,
  type DomainEvent 
} from '@phenotype-dev/ts-hex/domain';
import { Repository, type InputPort } from '@phenotype-dev/ts-hex/ports';

// 1. Define your domain entity
interface OrderId extends EntityId {}

class OrderIdImpl extends Uuid implements OrderId {
  static create(): OrderIdImpl {
    return new OrderIdImpl(crypto.randomUUID());
  }
}

// 2. Define your aggregate
class Order extends BaseAggregate<Order, OrderIdImpl> {
  private _status: OrderStatus = 'pending';

  constructor(id: OrderIdImpl) {
    super(id);
  }

  get status(): OrderStatus {
    return this._status;
  }

  confirm(): void {
    this._status = 'confirmed';
    this.addEvent(new OrderConfirmedEvent(this.id.value));
  }
}

// 3. Define your repository port
interface OrderRepository extends Repository<Order, OrderIdImpl> {}

// 4. Define your use case (input port)
interface CreateOrderInput {
  customerId: string;
  items: OrderItem[];
}

interface CreateOrderOutput {
  orderId: string;
}

interface CreateOrderUseCase extends InputPort {
  execute(input: CreateOrderInput): Promise<CreateOrderOutput>;
}
```

## Core Patterns

### Domain Layer

- **Entity**: Objects with identity (`BaseEntity`, `Uuid`)
- **ValueObject**: Immutable objects compared by value (`BaseValueObject`)
- **AggregateRoot**: Cluster of domain objects treated as one unit (`BaseAggregate`)
- **DomainEvent**: Something happened that's significant to the business (`BaseDomainEvent`)
- **DomainError**: Domain-level errors with code and message

### Ports Layer

- **InputPort**: Marker interface for driving ports
- **OutputPort**: Marker interface for driven ports
- **Repository**: Interface for entity persistence
- **EventStore**: Interface for event sourcing
- **MessageBus**: Interface for publishing events
- **UnitOfWork**: Interface for transactional operations

## Testing

```bash
npm test
npm run build
npm run lint
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

| Feature | ts-hex | nestjs | inversify |
|---------|--------|--------|----------|
| Hexagonal-first | ✅ | ❌ | ❌ |
| Zero deps in domain | ✅ | ❌ | ❌ |
| Type-safe ports | ✅ | ✅ | ✅ |
| Event sourcing | ✅ | ⚠️ | ❌ |
| Framework-agnostic | ✅ | ❌ | ⚠️ |

## License

MIT
