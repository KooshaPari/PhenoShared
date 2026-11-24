package inbound

import (
	"context"

	"{{ module_path }}/domain/entities"
	"{{ module_path }}/domain/valueobjects"
)

// UseCase defines the inbound port for application use cases
type UseCase interface {
	// Create creates a new entity
	Create(ctx context.Context, input CreateInput) (*entities.Entity, error)
	// GetByID retrieves an entity by ID
	GetByID(ctx context.Context, id string) (*entities.Entity, error)
	// Update updates an existing entity
	Update(ctx context.Context, input UpdateInput) (*entities.Entity, error)
	// Delete removes an entity
	Delete(ctx context.Context, id string) error
	// List returns all entities
	List(ctx context.Context) ([]*entities.Entity, error)
}

// Input DTOs
type CreateInput struct {
	Name        string
	Description string
}

type UpdateInput struct {
	ID          string
	Name        string
	Description string
}
