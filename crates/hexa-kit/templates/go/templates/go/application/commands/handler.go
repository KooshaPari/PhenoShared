package commands

import (
	"context"
	"fmt"

	"{{ module_path }}/domain/entities"
	"{{ module_path }}/domain/errors"
	"{{ module_path }}/domain/ports/inbound"
	"{{ module_path }}/domain/ports/outbound"
	"{{ module_path }}/domain/valueobjects"
)

// Service implements the UseCase interface
type Service struct {
	repo outbound.Repository
}

// NewService creates a new application service
func NewService(repo outbound.Repository) *Service {
	return &Service{repo: repo}
}

// Create creates a new entity
func (s *Service) Create(ctx context.Context, input inbound.CreateInput) (*entities.Entity, error) {
	if input.Name == "" {
		return nil, errors.ErrInvalidInput
	}

	entity, err := entities.NewExample(input.Name, input.Description)
	if err != nil {
		return nil, fmt.Errorf("creating entity: %w", err)
	}

	if err := s.repo.Save(ctx, entity); err != nil {
		return nil, fmt.Errorf("saving entity: %w", err)
	}

	return entity, nil
}

// GetByID retrieves an entity by ID
func (s *Service) GetByID(ctx context.Context, id string) (*entities.Entity, error) {
	entity, err := s.repo.FindByID(ctx, id)
	if err != nil {
		if errors.IsNotFound(err) {
			return nil, errors.ErrEntityNotFound
		}
		return nil, fmt.Errorf("finding entity: %w", err)
	}
	return entity, nil
}

// Update updates an existing entity
func (s *Service) Update(ctx context.Context, input inbound.UpdateInput) (*entities.Entity, error) {
	if input.ID == "" {
		return nil, errors.ErrInvalidInput
	}

	entity, err := s.repo.FindByID(ctx, input.ID)
	if err != nil {
		if errors.IsNotFound(err) {
			return nil, errors.ErrEntityNotFound
		}
		return nil, fmt.Errorf("finding entity: %w", err)
	}

	if err := entity.Rename(input.Name); err != nil {
		return nil, fmt.Errorf("updating entity: %w", err)
	}
	entity.Description = input.Description

	if err := s.repo.Save(ctx, entity); err != nil {
		return nil, fmt.Errorf("saving entity: %w", err)
	}

	return entity, nil
}

// Delete removes an entity
func (s *Service) Delete(ctx context.Context, id string) error {
	if !s.repo.Exists(ctx, id) {
		return errors.ErrEntityNotFound
	}

	if err := s.repo.Delete(ctx, id); err != nil {
		return fmt.Errorf("deleting entity: %w", err)
	}

	return nil
}

// List returns all entities
func (s *Service) List(ctx context.Context) ([]*entities.Entity, error) {
	entities, err := s.repo.FindAll(ctx)
	if err != nil {
		return nil, fmt.Errorf("listing entities: %w", err)
	}
	return entities, nil
}

// Ensure Service implements UseCase
var _ inbound.UseCase = (*Service)(nil)
