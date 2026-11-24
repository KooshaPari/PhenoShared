package adapters

import (
	"context"
	"sync"

	"github.com/phenotype-dev/go-hex/domain"
	"github.com/phenotype-dev/go-hex/ports"
)

// InMemoryRepository is an in-memory implementation of Repository
type InMemoryRepository[T any] struct {
	mu       sync.RWMutex
	entities map[string]T
}

// NewInMemoryRepository creates a new in-memory repository
func NewInMemoryRepository[T any]() *InMemoryRepository[T] {
	return &InMemoryRepository[T]{
		entities: make(map[string]T),
	}
}

// Save saves an entity
func (r *InMemoryRepository[T]) Save(ctx context.Context, entity T) (T, error) {
	r.mu.Lock()
	defer r.mu.Unlock()

	var id string
	switch e := any(entity).(type) {
	case domain.Entity:
		id = e.ID().String()
	default:
		// Use reflection or require ID method
	}

	r.entities[id] = entity
	return entity, nil
}

// FindByID finds an entity by ID
func (r *InMemoryRepository[T]) FindByID(ctx context.Context, id string) (T, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var zero T
	if entity, ok := r.entities[id]; ok {
		return entity, nil
	}
	return zero, domain.ErrNotFound
}

// Delete deletes an entity
func (r *InMemoryRepository[T]) Delete(ctx context.Context, id string) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	delete(r.entities, id)
	return nil
}

// FindAll finds all entities
func (r *InMemoryRepository[T]) FindAll(ctx context.Context) ([]T, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	entities := make([]T, 0, len(r.entities))
	for _, e := range r.entities {
		entities = append(entities, e)
	}
	return entities, nil
}

// Count returns the count of entities
func (r *InMemoryRepository[T]) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.entities)
}

// InMemoryEventStore is an in-memory event store
type InMemoryEventStore struct {
	mu     sync.RWMutex
	events map[string][]ports.Event
}

// NewInMemoryEventStore creates a new in-memory event store
func NewInMemoryEventStore() *InMemoryEventStore {
	return &InMemoryEventStore{
		events: make(map[string][]ports.Event),
	}
}

// Append appends events to the aggregate
func (s *InMemoryEventStore) Append(ctx context.Context, aggregateID string, evts []ports.Event, expectedVersion uint64) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	events := s.events[aggregateID]
	if uint64(len(events)) != expectedVersion {
		return domain.ErrConflict
	}

	s.events[aggregateID] = append(events, evts...)
	return nil
}

// GetEvents retrieves events for an aggregate
func (s *InMemoryEventStore) GetEvents(ctx context.Context, aggregateID string) ([]ports.Event, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	return s.events[aggregateID], nil
}
