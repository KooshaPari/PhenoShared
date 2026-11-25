package ports

import (
	"context"
	"time"

	"github.com/phenotype-dev/go-hex/domain"
)

// InputPort is the marker interface for input ports (driving ports)
type InputPort interface {
	isInputPort()
}

// OutputPort is the marker interface for output ports (driven ports)
type OutputPort interface {
	isOutputPort()
}

// Event is the interface that all domain events implement
// This is an alias to allow the ports layer to reference events
type Event = domain.DomainEvent

// Repository is the interface for entity persistence
type Repository[T any] interface {
	Save(ctx context.Context, entity T) (T, error)
	FindByID(ctx context.Context, id string) (T, error)
	Delete(ctx context.Context, id string) error
	FindAll(ctx context.Context) ([]T, error)
}

// QueryRepository is the interface for read operations
type QueryRepository[T any] interface {
	FindByFilter(ctx context.Context, filter Filter) ([]T, error)
	Count(ctx context.Context, filter Filter) (int64, error)
}

// EventStore is the interface for event sourcing
type EventStore interface {
	Append(ctx context.Context, aggregateID string, events []Event, expectedVersion uint64) error
	GetEvents(ctx context.Context, aggregateID string) ([]Event, error)
}

// MessageBus is the interface for publishing events
type MessageBus interface {
	Publish(ctx context.Context, topic string, event Event) error
	Subscribe(topic string, handler EventHandler)
}

// EventHandler is the interface for event handlers
type EventHandler interface {
	Handle(ctx context.Context, event Event) error
}

// Filter represents query filters
type Filter struct {
	Conditions []Condition
	Limit      int
	Offset     int
}

// Condition represents a single filter condition
type Condition struct {
	Field    string
	Operator Operator
	Value    any
}

// Operator represents filter operators
type Operator string

const (
	OpEq         Operator = "eq"
	OpNe         Operator = "ne"
	OpGt         Operator = "gt"
	OpLt         Operator = "lt"
	OpGte        Operator = "gte"
	OpLte        Operator = "lte"
	OpContains   Operator = "contains"
	OpStartsWith Operator = "startsWith"
	OpIn         Operator = "in"
)

// NewFilter creates a new filter
func NewFilter() *Filter {
	return &Filter{
		Conditions: make([]Condition, 0),
		Limit:      100,
	}
}

// WithCondition adds a condition to the filter
func (f *Filter) WithCondition(field string, op Operator, value any) *Filter {
	f.Conditions = append(f.Conditions, Condition{
		Field:    field,
		Operator: op,
		Value:    value,
	})
	return f
}

// WithLimit sets the result limit
func (f *Filter) WithLimit(limit int) *Filter {
	f.Limit = limit
	return f
}

// WithOffset sets the result offset
func (f *Filter) WithOffset(offset int) *Filter {
	f.Offset = offset
	return f
}

// UnitOfWork manages transactional operations
type UnitOfWork interface {
	Begin(ctx context.Context) error
	Commit(ctx context.Context) error
	Rollback(ctx context.Context) error
	GetRepository(entityName string) any
}

// ExternalService is the interface for calling external services
type ExternalService[Req, Res any] interface {
	Call(ctx context.Context, request Req) (Res, error)
}

// HealthChecker is the interface for health checks
type HealthChecker interface {
	Check(ctx context.Context) error
}

// HealthStatus represents the health status
type HealthStatus struct {
	Status    string
	Timestamp time.Time
	Message   string
}
