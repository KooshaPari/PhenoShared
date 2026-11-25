package core

import "context"

// Status reports the current health of a component.
type Status struct {
	Healthy bool
	Message string
}

// Tool describes a built-in or registered capability.
type Tool struct {
	Name        string
	Description string
}

// Logger captures the minimal logging contract used by adapters.
type Logger interface {
	Printf(format string, args ...any)
}

// Dispatcher executes registered tool calls.
type Dispatcher interface {
	Dispatch(ctx context.Context, name string, args []string) ([]byte, error)
	Health(ctx context.Context) Status
	ListTools() []Tool
}

// Registry stores tools by name.
type Registry interface {
	Register(name string, tool Tool)
	Get(name string) (Tool, bool)
	Names() []string
}
