# HexaGo — Specification

Lightweight, dependency-free hexagonal architecture kit for Go applications.

## Architecture

```
┌───────────────────────────────────────────────┐
│             Adapters (Infrastructure)          │
│  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐ │
│  │ REST  │  │ gRPC  │  │  CLI  │  │  DB   │ │
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
│  Pure Go, 0 deps │  │  UseCases, DTOs        │
│  Entities, VOs,  │  │  Commands, Queries     │
│  Aggregates      │  │  Handlers              │
└──────────────────┘  └────────────────────────┘
```

## Components

| Package | Role | Key Types |
|---------|------|-----------|
| domain | Core building blocks | BaseEntity, ValueObject, AggregateRoot, DomainEvent |
| ports | Interface contracts | InputPort, OutputPort, Repository, EventStore |
| application | Use case orchestration | UseCase, Command, Query, DTO |

## Data Models

```go
type EntityID string

type BaseEntity struct {
    id        EntityID
    createdAt time.Time
    updatedAt time.Time
}

type ValueObject interface {
    Equals(other ValueObject) bool
}

type AggregateRoot interface {
    ID() EntityID
    DomainEvents() []DomainEvent
    ClearEvents()
}

type DomainEvent interface {
    EventName() string
    OccurredAt() time.Time
}
```

## API Design

```go
// Port definition (input - driving)
type CreateOrderInput struct {
    CustomerID string
    Items      []OrderItemInput
}

type CreateOrderUseCase interface {
    Execute(ctx context.Context, input CreateOrderInput) (CreateOrderOutput, error)
}

// Port definition (output - driven)
type OrderRepository interface {
    Save(ctx context.Context, order *Order) (*Order, error)
    FindByID(ctx context.Context, id domain.EntityID) (*Order, error)
}

// Adapter (REST)
type OrderHandler struct {
    uc CreateOrderUseCase
}

func (h *OrderHandler) CreateOrder(w http.ResponseWriter, r *http.Request) {
    var input CreateOrderInput
    json.NewDecoder(r.Body).Decode(&input)
    output, err := h.uc.Execute(r.Context(), input)
    // handle response
}
```

## Package Layout

```
go-hex/
├── domain/
│   ├── entity.go
│   ├── value_object.go
│   ├── aggregate.go
│   └── event.go
├── ports/
│   ├── input_port.go
│   ├── output_port.go
│   └── repository.go
├── application/
│   ├── usecase.go
│   ├── command.go
│   └── query.go
└── go.mod
```

## Performance Targets

| Metric | Target |
|--------|--------|
| Zero external dependencies | domain package |
| Go version | 1.21+ |
| Build time | < 3s |
| Test suite | < 5s |
| go vet | 0 issues |
| Test coverage | > 90% |

## Quality Gates

- `go build ./...` — clean build
- `go test -cover ./...` — coverage > 90%
- `go vet ./...` — no issues
- `go fmt ./...` — formatted
- Domain layer imports zero external packages
- All public interfaces documented
