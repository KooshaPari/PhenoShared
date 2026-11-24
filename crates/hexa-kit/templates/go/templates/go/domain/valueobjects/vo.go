package valueobjects

import (
	"time"
)

// EntityID is a value object representing a unique entity identifier
type EntityID struct {
	value string
}

func NewEntityID(value string) (*EntityID, error) {
	if value == "" {
		return nil, ErrInvalidID
	}
	return &EntityID{value: value}, nil
}

func (e *EntityID) String() string {
	return e.value
}

func (e *EntityID) Equals(other *EntityID) bool {
	if other == nil {
		return false
	}
	return e.value == other.value
}

// EntityStatus represents the status of an entity
type EntityStatus string

const (
	StatusPending  EntityStatus = "pending"
	StatusActive   EntityStatus = "active"
	StatusArchived  EntityStatus = "archived"
)

func (s EntityStatus) IsValid() bool {
	switch s {
	case StatusPending, StatusActive, StatusArchived:
		return true
	}
	return false
}

// Timestamps holds creation and update times
type Timestamps struct {
	CreatedAt time.Time
	UpdatedAt time.Time
}
