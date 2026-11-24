package entities

import (
	"time"

	"github.com/google/uuid"
)

// Entity is the base for all domain entities with identity
type Entity struct {
	ID        uuid.UUID
	CreatedAt time.Time
	UpdatedAt time.Time
}

// NewEntity creates a new entity with generated ID
func NewEntity() *Entity {
	return &Entity{
		ID:        uuid.New(),
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}
}

// Touch updates the UpdatedAt timestamp
func (e *Entity) Touch() {
	e.UpdatedAt = time.Now()
}

// Equals checks equality based on ID
func (e *Entity) Equals(other *Entity) bool {
	if other == nil {
		return false
	}
	return e.ID == other.ID
}
