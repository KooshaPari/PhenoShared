package outbound

import (
	"context"

	"{{ module_path }}/domain/entities"
	"{{ module_path }}/domain/valueobjects"
)

// Repository defines the outbound port for persistence
type Repository interface {
	// Save persists an entity
	Save(ctx context.Context, entity *entities.Entity) error
	// FindByID retrieves an entity by ID
	FindByID(ctx context.Context, id string) (*entities.Entity, error)
	// FindAll returns all entities
	FindAll(ctx context.Context) ([]*entities.Entity, error)
	// Delete removes an entity
	Delete(ctx context.Context, id string) error
	// Exists checks if an entity exists
	Exists(ctx context.Context, id string) bool
}

// UnitOfWork defines the outbound port for transaction management
type UnitOfWork interface {
	// Repository returns a repository instance
	Repository() Repository
	// Commit commits the current transaction
	Commit(ctx context.Context) error
	// Rollback rolls back the current transaction
	Rollback(ctx context.Context) error
}
