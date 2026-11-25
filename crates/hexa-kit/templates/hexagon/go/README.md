# Go-Hex: Hexagonal Architecture Kit for Go

A lightweight, dependency-free hexagonal architecture kit for Go applications.

## Philosophy

Go-Hex provides the structural patterns for building applications with **Hexagonal Architecture** (Ports & Adapters) while respecting Go's idioms and simplicity.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Adapters Layer                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   REST   │  │   gRPC   │  │    CLI    │            │
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
│                      Domain Layer                        │
│  Pure business logic - ZERO external dependencies       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Entities │  │ValueObjs │  │Aggregates│            │
│  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────┘
         │             │             │
         ▼             ▼             ▼
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ UseCases │  │   DTOs   │  │ Handlers │            │
│  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────────┘
```

## Installation

```bash
go get github.com/phenotype-dev/go-hex
```

## Quick Start

```go
package main

import (
    "context"
    
    "github.com/phenotype-dev/go-hex/domain"
    "github.com/phenotype-dev/go-hex/ports"
    "github.com/phenotype-dev/go-hex/application"
)

// 1. Define your domain entity
type Order struct {
    domain.BaseEntity
    Items     []OrderItem
    Status    OrderStatus
    TotalCents int64
}

type OrderStatus string

const (
    OrderStatusPending   OrderStatus = "pending"
    OrderStatusConfirmed OrderStatus = "confirmed"
    OrderStatusShipped   OrderStatus = "shipped"
)

// 2. Define your repository port (driven port)
type OrderRepository interface {
    Save(ctx context.Context, order *Order) (*Order, error)
    FindByID(ctx context.Context, id domain.EntityID) (*Order, error)
    FindAll(ctx context.Context) ([]*Order, error)
}

// 3. Define your use case (input port)
type CreateOrderInput struct {
    CustomerID string
    Items     []OrderItemInput
}

type CreateOrderOutput struct {
    OrderID domain.EntityID
}

type CreateOrderUseCase interface {
    Execute(ctx context.Context, input CreateOrderInput) (CreateOrderOutput, error)
}

// 4. Implement the use case
type createOrderUseCase struct {
    repo OrderRepository
}

func NewCreateOrderUseCase(repo OrderRepository) *createOrderUseCase {
    return &createOrderUseCase{repo: repo}
}

func (uc *createOrderUseCase) Execute(ctx context.Context, input CreateOrderInput) (CreateOrderOutput, error) {
    order := &Order{
        BaseEntity: *domain.NewBaseEntity(domain.NewEntityID()),
        Status:     OrderStatusPending,
        TotalCents: calculateTotal(input.Items),
    }
    
    saved, err := uc.repo.Save(ctx, order)
    if err != nil {
        return CreateOrderOutput{}, err
    }
    
    return CreateOrderOutput{OrderID: saved.ID()}, nil
}

// 5. Create your adapter (REST handler)
type OrderHandler struct {
    createOrderUC CreateOrderUseCase
}

func (h *OrderHandler) CreateOrder(w http.ResponseWriter, r *http.Request) {
    var input CreateOrderInput
    json.NewDecoder(r.Body).Decode(&input)
    
    output, err := h.createOrderUC.Execute(r.Context(), input)
    if err != nil {
        http.Error(w, err.Error(), 500)
        return
    }
    
    json.NewEncoder(w).Encode(output)
}
```

## Core Patterns

### Domain Layer

- **Entity**: Objects with identity
- **ValueObject**: Immutable objects compared by value
- **Aggregate**: Cluster of domain objects treated as one unit
- **DomainEvent**: Something happened that's significant to the business
- **DomainService**: Operation that doesn't belong to an entity

### Ports Layer

- **InputPort (Driving)**: Interface used by adapters to trigger use cases
- **OutputPort (Driven)**: Interface implemented by infrastructure for external concerns

### Application Layer

- **UseCase**: Single unit of application logic
- **Command**: Input for write operations
- **Query**: Input for read operations
- **DTO**: Data transfer objects

### Infrastructure Layer

- **Adapters**: Concrete implementations of output ports
- **REST**, **gRPC**, **CLI**: Driving adapters

## Testing

```bash
go test ./...        # Run all tests
go test -cover ./... # With coverage
go vet ./...         # Lint
go fmt ./...         # Format
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

| Feature | go-hex | go-clean | go-kit |
|---------|--------|----------|--------|
| Hexagonal-first | ✅ | ❌ | ❌ |
| Zero deps in domain | ✅ | ❌ | ❌ |
| Generic ports | ✅ | ❌ | ❌ |
| Event sourcing | ✅ | ❌ | ❌ |
| CQRS support | ✅ | ❌ | ✅ |

## License

MIT
