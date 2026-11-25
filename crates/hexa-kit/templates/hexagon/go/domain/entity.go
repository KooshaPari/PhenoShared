// Package domain contains pure business logic with no external dependencies.
package domain

import (
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"
)

// EntityID represents a unique identifier for entities
type EntityID = uuid.UUID

// NewEntityID creates a new unique entity ID
func NewEntityID() EntityID {
	return uuid.New()
}

// ParseEntityID parses a string into an entity ID
func ParseEntityID(s string) (EntityID, error) {
	return uuid.Parse(s)
}

// Entity is the interface that all domain entities implement
type Entity interface {
	ID() EntityID
	Equals(Entity) bool
}

// BaseEntity provides common entity functionality
type BaseEntity struct {
	id        EntityID
	createdAt time.Time
	updatedAt time.Time
}

// NewBaseEntity creates a new base entity
func NewBaseEntity(id EntityID) *BaseEntity {
	now := time.Now()
	return &BaseEntity{
		id:        id,
		createdAt: now,
		updatedAt: now,
	}
}

// ID returns the entity's unique identifier
func (e *BaseEntity) ID() EntityID {
	return e.id
}

// CreatedAt returns when the entity was created
func (e *BaseEntity) CreatedAt() time.Time {
	return e.createdAt
}

// UpdatedAt returns when the entity was last updated
func (e *BaseEntity) UpdatedAt() time.Time {
	return e.updatedAt
}

// Touch updates the updatedAt timestamp
func (e *BaseEntity) Touch() {
	e.updatedAt = time.Now()
}

// Equals checks if two entities have the same ID
func (e *BaseEntity) Equals(other Entity) bool {
	if other == nil {
		return false
	}
	return e.id == other.ID()
}

// DomainError represents a domain-level error
type DomainError struct {
	Code    string
	Message string
	Err     error
}

func (e *DomainError) Error() string {
	if e.Err != nil {
		return e.Code + ": " + e.Message + " - " + e.Err.Error()
	}
	return e.Code + ": " + e.Message
}

func (e *DomainError) Unwrap() error {
	return e.Err
}

// NewDomainError creates a new domain error
func NewDomainError(code, message string) *DomainError {
	return &DomainError{Code: code, Message: message}
}

// NewDomainErrorf creates a new domain error with formatted message
func NewDomainErrorf(code, format string, args ...interface{}) *DomainError {
	return &DomainError{Code: code, Message: fmt.Sprintf(format, args...)}
}

// ErrNotFound is returned when an entity is not found
var ErrNotFound = errors.New("entity not found")

// ErrInvalidInput is returned when input validation fails
var ErrInvalidInput = errors.New("invalid input")

// ErrConflict is returned when there's a business rule conflict
var ErrConflict = errors.New("conflict")
