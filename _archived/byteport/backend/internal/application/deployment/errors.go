package deployment

import "fmt"

// ApplicationError represents an application-level error
type ApplicationError struct {
	Code       string
	Message    string
	StatusCode int
	Err        error
}

func (e *ApplicationError) Error() string {
	if e.Err != nil {
		return fmt.Sprintf("%s: %s (%v)", e.Code, e.Message, e.Err)
	}
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *ApplicationError) Unwrap() error {
	return e.Err
}

// HTTP Status Codes
const (
	StatusBadRequest          = 400
	StatusUnauthorized        = 401
	StatusForbidden           = 403
	StatusNotFound            = 404
	StatusConflict            = 409
	StatusInternalServerError = 500
)

// Error constructors

func NewValidationError(message string) *ApplicationError {
	return &ApplicationError{
		Code:       "VALIDATION_ERROR",
		Message:    message,
		StatusCode: StatusBadRequest,
	}
}

func NewNotFoundError(resource string) *ApplicationError {
	return &ApplicationError{
		Code:       "NOT_FOUND",
		Message:    fmt.Sprintf("%s not found", resource),
		StatusCode: StatusNotFound,
	}
}

func NewUnauthorizedError(message string) *ApplicationError {
	return &ApplicationError{
		Code:       "UNAUTHORIZED",
		Message:    message,
		StatusCode: StatusUnauthorized,
	}
}

func NewForbiddenError(message string) *ApplicationError {
	return &ApplicationError{
		Code:       "FORBIDDEN",
		Message:    message,
		StatusCode: StatusForbidden,
	}
}

func NewConflictError(message string) *ApplicationError {
	return &ApplicationError{
		Code:       "CONFLICT",
		Message:    message,
		StatusCode: StatusConflict,
	}
}

func NewInternalError(message string, err error) *ApplicationError {
	return &ApplicationError{
		Code:       "INTERNAL_ERROR",
		Message:    message,
		StatusCode: StatusInternalServerError,
		Err:        err,
	}
}
