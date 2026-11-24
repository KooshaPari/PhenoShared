package entities

// Example represents a domain entity with state machine
type Example struct {
	*Entity
	Name        string
	Description string
	Status      ExampleStatus
}

// ExampleStatus represents the state of an Example
type ExampleStatus string

const (
	StatusPending   ExampleStatus = "pending"
	StatusActive   ExampleStatus = "active"
	StatusCompleted ExampleStatus = "completed"
	StatusArchived  ExampleStatus = "archived"
)

// ValidStatuses contains all valid status values
var ValidStatuses = []ExampleStatus{StatusPending, StatusActive, StatusCompleted, StatusArchived}

// IsValid checks if the status is valid
func (s ExampleStatus) IsValid() bool {
	for _, valid := range ValidStatuses {
		if s == valid {
			return true
		}
	}
	return false
}

// NewExample creates a new example entity
func NewExample(name, description string) *Example {
	return &Example{
		Entity:      NewEntity(),
		Name:        name,
		Description: description,
		Status:      StatusPending,
	}
}

// Validate performs domain validation
func (e *Example) Validate() error {
	if e.Name == "" {
		return errNameRequired
	}
	if len(e.Name) > 100 {
		return errNameTooLong
	}
	return nil
}

// Activate transitions the entity to active state
func (e *Example) Activate() error {
	if e.Status == StatusArchived {
		return ErrInvalidStateTransition
	}
	e.Status = StatusActive
	e.Touch()
	return nil
}

// Complete transitions the entity to completed state
func (e *Example) Complete() error {
	if e.Status != StatusActive {
		return ErrInvalidStateTransition
	}
	e.Status = StatusCompleted
	e.Touch()
	return nil
}

// Archive transitions the entity to archived state
func (e *Example) Archive() {
	if e.Status != StatusArchived {
		e.Status = StatusArchived
		e.Touch()
	}
}

// Domain errors
var (
	errNameRequired            = NewDomainError(ErrInvalidInput, "name", "NAME_REQUIRED", "name is required")
	errNameTooLong            = NewDomainError(ErrInvalidInput, "name", "NAME_TOO_LONG", "name must be less than 100 characters")
	ErrInvalidStateTransition = NewDomainError(ErrDomainViolation, "status", "INVALID_TRANSITION", "invalid state transition")
)

// DomainError wraps domain errors with context
type DomainError struct {
	Err     error
	Field   string
	Code    string
	Message string
}

func (e *DomainError) Error() string {
	if e.Field != "" {
		return e.Field + ": " + e.Message
	}
	return e.Message
}

func (e *DomainError) Unwrap() error {
	return e.Err
}
