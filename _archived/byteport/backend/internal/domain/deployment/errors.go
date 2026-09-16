package deployment

import "fmt"

// DomainError represents a domain-specific error
type DomainError struct {
	Code    string
	Message string
	Err     error
}

func (e *DomainError) Error() string {
	if e.Err != nil {
		return fmt.Sprintf("%s: %s (%v)", e.Code, e.Message, e.Err)
	}
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *DomainError) Unwrap() error {
	return e.Err
}

// Error constructors

func NewInvalidStatusTransitionError(from, to Status) error {
	return &DomainError{
		Code:    "INVALID_STATUS_TRANSITION",
		Message: fmt.Sprintf("cannot transition from %s to %s", from, to),
	}
}

func NewDeploymentNotFoundError(uuid string) error {
	return &DomainError{
		Code:    "DEPLOYMENT_NOT_FOUND",
		Message: fmt.Sprintf("deployment with UUID %s not found", uuid),
	}
}

func NewInvalidDeploymentError(message string) error {
	return &DomainError{
		Code:    "INVALID_DEPLOYMENT",
		Message: message,
	}
}

func NewPermissionDeniedError(action, resource string) error {
	return &DomainError{
		Code:    "PERMISSION_DENIED",
		Message: fmt.Sprintf("permission denied for action %s on resource %s", action, resource),
	}
}
