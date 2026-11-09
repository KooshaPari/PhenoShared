package domain

import "fmt"

// EnvironmentFactory is a constructor function for an Environment adapter.
type EnvironmentFactory func() Environment

// Registry maps BackendType values to their adapter factories.
// Use Register to add adapters at init time; use New to instantiate.
type Registry struct {
	factories map[BackendType]EnvironmentFactory
}

// NewRegistry returns an empty Registry.
func NewRegistry() *Registry {
	return &Registry{factories: make(map[BackendType]EnvironmentFactory)}
}

// Register adds a factory for the given backend type.
// Panics if the backend is already registered (fail loudly — see governance).
func (r *Registry) Register(backend BackendType, factory EnvironmentFactory) {
	if _, exists := r.factories[backend]; exists {
		panic(fmt.Sprintf("devenv-abstraction: backend %q already registered", backend))
	}
	r.factories[backend] = factory
}

// New constructs and returns an Environment for the requested backend.
// Returns a descriptive error if the backend is not registered.
func (r *Registry) New(backend BackendType) (Environment, error) {
	factory, ok := r.factories[backend]
	if !ok {
		return nil, fmt.Errorf("devenv-abstraction: backend %q is not registered; available: %v", backend, r.Available())
	}
	return factory(), nil
}

// Available returns the list of registered backend types.
func (r *Registry) Available() []BackendType {
	keys := make([]BackendType, 0, len(r.factories))
	for k := range r.factories {
		keys = append(keys, k)
	}
	return keys
}
