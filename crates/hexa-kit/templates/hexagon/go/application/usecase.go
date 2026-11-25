// Package application contains use cases and application services
package application

import (
	"context"
	"fmt"
)

// UseCase is the interface for application use cases
type UseCase[I, O any] interface {
	Execute(ctx context.Context, input I) (O, error)
}

// CommandUseCase is a use case for commands (write operations)
type CommandUseCase[C, R any] interface {
	Execute(ctx context.Context, command C) (R, error)
}

// QueryUseCase is a use case for queries (read operations)
type QueryUseCase[Q, R any] interface {
	Execute(ctx context.Context, query Q) (R, error)
}

// UseCaseFunc is a function adapter for use cases
type UseCaseFunc[I, O any] func(ctx context.Context, input I) (O, error)

// Execute implements UseCase
func (f UseCaseFunc[I, O]) Execute(ctx context.Context, input I) (O, error) {
	return f(ctx, input)
}

// CommandFunc is a function adapter for command use cases
type CommandFunc[C, R any] func(ctx context.Context, command C) (R, error)

// Execute implements CommandUseCase
func (f CommandFunc[C, R]) Execute(ctx context.Context, command C) (R, error) {
	return f(ctx, command)
}

// QueryFunc is a function adapter for query use cases
type QueryFunc[Q, R any] func(ctx context.Context, query Q) (R, error)

// Execute implements QueryUseCase
func (f QueryFunc[Q, R]) Execute(ctx context.Context, query Q) (R, error) {
	return f(ctx, query)
}

// CommandHandler handles commands
type CommandHandler[C, R any] struct {
	uc CommandUseCase[C, R]
}

// NewCommandHandler creates a new command handler
func NewCommandHandler[C, R any](uc CommandUseCase[C, R]) *CommandHandler[C, R] {
	return &CommandHandler[C, R]{uc: uc}
}

// Handle handles a command
func (h *CommandHandler[C, R]) Handle(ctx context.Context, command C) (R, error) {
	return h.uc.Execute(ctx, command)
}

// QueryHandler handles queries
type QueryHandler[Q, R any] struct {
	uc QueryUseCase[Q, R]
}

// NewQueryHandler creates a new query handler
func NewQueryHandler[Q, R any](uc QueryUseCase[Q, R]) *QueryHandler[Q, R] {
	return &QueryHandler[Q, R]{uc: uc}
}

// Handle handles a query
func (h *QueryHandler[Q, R]) Handle(ctx context.Context, query Q) (R, error) {
	return h.uc.Execute(ctx, query)
}

// ApplicationError represents application-level errors
type ApplicationError struct {
	Code    string
	Message string
	Err     error
}

func (e *ApplicationError) Error() string {
	if e.Err != nil {
		return fmt.Sprintf("%s: %s - %v", e.Code, e.Message, e.Err)
	}
	return fmt.Sprintf("%s: %s", e.Code, e.Message)
}

func (e *ApplicationError) Unwrap() error {
	return e.Err
}

// NewApplicationError creates a new application error
func NewApplicationError(code, message string) *ApplicationError {
	return &ApplicationError{Code: code, Message: message}
}
