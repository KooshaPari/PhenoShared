package domain

import (
	"time"
)

// AggregateRoot is the interface that all aggregates implement
type AggregateRoot interface {
	Entity
	Version() uint64
	PullEvents() []DomainEvent
	AddEvent(event DomainEvent)
}

// BaseAggregate provides common aggregate functionality
type BaseAggregate struct {
	BaseEntity
	version       uint64
	pendingEvents []DomainEvent
}

// NewBaseAggregate creates a new base aggregate
func NewBaseAggregate(id EntityID) *BaseAggregate {
	return &BaseAggregate{
		BaseEntity:    *NewBaseEntity(id),
		version:       1,
		pendingEvents: make([]DomainEvent, 0),
	}
}

// Version returns the aggregate version
func (a *BaseAggregate) Version() uint64 {
	return a.version
}

// PullEvents returns and clears pending domain events
func (a *BaseAggregate) PullEvents() []DomainEvent {
	events := a.pendingEvents
	a.pendingEvents = make([]DomainEvent, 0)
	return events
}

// AddEvent adds a domain event to the aggregate
func (a *BaseAggregate) AddEvent(event DomainEvent) {
	a.pendingEvents = append(a.pendingEvents, event)
	a.version++
	a.Touch()
}

// DomainEvent is the interface that all domain events implement
type DomainEvent interface {
	EventType() string
	OccurredAt() Time
	AggregateID() EntityID
}

// Time wraps time.Time for domain events
type Time struct {
	value int64 // Unix timestamp
}

// NewTime creates a new time
func NewTime() Time {
	return Time{value: nowUnix()}
}

// FromTime creates a Time from a time.Time
func FromTime(t time.Time) Time {
	return Time{value: t.Unix()}
}

// Unix returns the Unix timestamp
func (t Time) Unix() int64 {
	return t.value
}

// ToTime converts back to time.Time
func (t Time) ToTime() time.Time {
	return time.Unix(t.value, 0)
}

// BaseDomainEvent provides common domain event functionality
type BaseDomainEvent struct {
	eventType   string
	occurredAt  Time
	aggregateID EntityID
	metadata    map[string]string
}

// NewBaseDomainEvent creates a new base domain event
func NewBaseDomainEvent(eventType string, aggregateID EntityID) *BaseDomainEvent {
	return &BaseDomainEvent{
		eventType:   eventType,
		occurredAt:  NewTime(),
		aggregateID: aggregateID,
		metadata:    make(map[string]string),
	}
}

// EventType returns the event type
func (e *BaseDomainEvent) EventType() string {
	return e.eventType
}

// OccurredAt returns when the event occurred
func (e *BaseDomainEvent) OccurredAt() Time {
	return e.occurredAt
}

// AggregateID returns the aggregate ID
func (e *BaseDomainEvent) AggregateID() EntityID {
	return e.aggregateID
}

// WithMetadata adds metadata to the event
func (e *BaseDomainEvent) WithMetadata(key, value string) *BaseDomainEvent {
	e.metadata[key] = value
	return e
}

// GetMetadata returns metadata value
func (e *BaseDomainEvent) GetMetadata(key string) string {
	return e.metadata[key]
}

// DomainService is the interface for domain services
type DomainService interface {
	Execute() error
}

func nowUnix() int64 {
	return time.Now().Unix()
}
