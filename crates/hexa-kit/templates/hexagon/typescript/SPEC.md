# HexaType — Specification

Lightweight, dependency-free hexagonal architecture kit for TypeScript/JavaScript.

## Architecture

```
┌───────────────────────────────────────────────┐
│             Adapters (Infrastructure)          │
│  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐ │
│  │ Express│  │ gRPC  │  │  CLI  │  │ Prisma│ │
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
│  Pure TS, 0 deps │  │  UseCases, DTOs        │
│  Entities, VOs,  │  │  Commands, Queries     │
│  Aggregates      │  │  Handlers              │
└──────────────────┘  └────────────────────────┘
```

## Components

| Module      | Role                   | Key Types                                                   |
| ----------- | ---------------------- | ----------------------------------------------------------- |
| domain      | Core building blocks   | BaseEntity, BaseValueObject, BaseAggregate, BaseDomainEvent |
| ports       | Interface contracts    | InputPort, OutputPort, Repository, EventStore, UnitOfWork   |
| application | Use case orchestration | UseCase, Command, Query                                     |

## Data Models

```typescript
interface EntityId {
  readonly value: string;
}

class BaseEntity<T extends EntityId> {
  constructor(public readonly id: T) {}
}

class BaseValueObject {
  abstract equals(other: this): boolean;
}

class BaseAggregate<E extends Entity, T extends EntityId> extends BaseEntity<T> {
  private _events: DomainEvent[] = [];

  protected addEvent(event: DomainEvent): void {
    this._events.push(event);
  }

  collectEvents(): DomainEvent[] {
    const events = [...this._events];
    this._events = [];
    return events;
  }
}

interface DomainEvent {
  readonly eventName: string;
  readonly occurredAt: Date;
}

class DomainError extends Error {
  constructor(
    public readonly code: string,
    message: string
  ) {
    super(message);
  }
}
```

## API Design

```typescript
import {
  BaseEntity,
  Uuid,
  BaseAggregate,
  type EntityId,
  type DomainEvent,
} from '@phenotype-dev/ts-hex/domain';
import { type Repository, type InputPort } from '@phenotype-dev/ts-hex/ports';

interface OrderId extends EntityId {}

class Order extends BaseAggregate<Order, OrderId> {
  private _status: 'pending' | 'confirmed' = 'pending';

  confirm(): void {
    this._status = 'confirmed';
    this.addEvent({ eventName: 'OrderConfirmed', occurredAt: new Date() });
  }
}

interface OrderRepository extends Repository<Order, OrderId> {}

interface CreateOrderUseCase extends InputPort {
  execute(input: CreateOrderInput): Promise<CreateOrderOutput>;
}
```

## Package Layout

```
ts-hex/
├── src/
│   ├── domain/
│   │   ├── index.ts
│   │   ├── entity.ts
│   │   ├── value-object.ts
│   │   ├── aggregate.ts
│   │   └── event.ts
│   ├── ports/
│   │   ├── index.ts
│   │   ├── input-port.ts
│   │   ├── output-port.ts
│   │   └── repository.ts
│   └── application/
│       ├── index.ts
│       ├── usecase.ts
│       ├── command.ts
│       └── query.ts
├── package.json
└── tsconfig.json
```

## Performance Targets

| Metric                    | Target         |
| ------------------------- | -------------- |
| Zero runtime dependencies | domain module  |
| TypeScript version        | 5.0+           |
| Build time (tsc)          | < 5s           |
| Test suite (vitest)       | < 10s          |
| Bundle size (domain)      | < 8KB minified |
| Test coverage             | > 90%          |

## Quality Gates

- `npm test` — all tests pass
- `npm run build` — clean tsc compilation
- `npm run lint` — 0 errors
- tsconfig strict mode enabled
- Domain module imports zero external packages
- All public types fully typed (no `any`)
