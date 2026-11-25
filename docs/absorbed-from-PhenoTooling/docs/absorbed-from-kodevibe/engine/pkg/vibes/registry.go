// Package vibes provides code quality analysis and vibe checking functionality.
// It includes checkers for security, code quality, performance, file structure,
// git best practices, dependency management, and documentation standards.
package vibes

import (
	"context"
	"fmt"
	"sync"

	"kodevibe/internal/models"
)

// Checker interface defines the contract for all vibe checkers
type Checker interface {
	// Check performs the vibe check on the provided files
	Check(ctx context.Context, files []string) ([]models.Issue, error)

	// Name returns the name of the vibe checker
	Name() string

	// Type returns the vibe type
	Type() models.VibeType

	// Configure configures the checker with the provided settings
	Configure(config models.VibeConfig) error

	// Supports returns true if the checker supports the given file
	Supports(filename string) bool
}

// Registry manages all available vibe checkers
type Registry struct {
	checkers map[models.VibeType]Checker
	mu       sync.RWMutex
}

// NewRegistry creates a new vibe registry
func NewRegistry() *Registry {
	return &Registry{
		checkers: make(map[models.VibeType]Checker),
	}
}

// RegisterChecker registers a vibe checker
func (r *Registry) RegisterChecker(checker Checker) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	if checker == nil {
		return fmt.Errorf("checker cannot be nil")
	}

	vibeType := checker.Type()
	if _, exists := r.checkers[vibeType]; exists {
		return fmt.Errorf("checker for vibe type %s already registered", vibeType)
	}

	r.checkers[vibeType] = checker
	return nil
}

// GetChecker returns a vibe checker for the specified type
func (r *Registry) GetChecker(vibeType models.VibeType) (Checker, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	checker, exists := r.checkers[vibeType]
	if !exists {
		return nil, fmt.Errorf("no checker registered for vibe type %s", vibeType)
	}

	return checker, nil
}

// GetAllCheckers returns all registered checkers
func (r *Registry) GetAllCheckers() map[models.VibeType]Checker {
	r.mu.RLock()
	defer r.mu.RUnlock()

	checkers := make(map[models.VibeType]Checker)
	for k, v := range r.checkers {
		checkers[k] = v
	}

	return checkers
}

// ListAvailableVibes returns a list of available vibe types
func (r *Registry) ListAvailableVibes() []models.VibeType {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var vibes []models.VibeType
	for vibeType := range r.checkers {
		vibes = append(vibes, vibeType)
	}

	return vibes
}

// RegisterAllVibes registers all built-in vibe checkers
func (r *Registry) RegisterAllVibes(config *models.Configuration) error {
	// Register Security Vibe
	securityChecker := NewSecurityChecker()
	if securityConfig, exists := config.Vibes[models.VibeTypeSecurity]; exists {
		if err := securityChecker.Configure(securityConfig); err != nil {
			return fmt.Errorf("failed to configure security checker: %w", err)
		}
	}
	if err := r.RegisterChecker(securityChecker); err != nil {
		return fmt.Errorf("failed to register security checker: %w", err)
	}

	// Register Code Vibe
	codeChecker := NewCodeChecker()
	if codeConfig, exists := config.Vibes[models.VibeTypeCode]; exists {
		if err := codeChecker.Configure(codeConfig); err != nil {
			return fmt.Errorf("failed to configure code checker: %w", err)
		}
	}
	if err := r.RegisterChecker(codeChecker); err != nil {
		return fmt.Errorf("failed to register code checker: %w", err)
	}

	// Register Performance Vibe
	performanceChecker := NewPerformanceChecker()
	if perfConfig, exists := config.Vibes[models.VibeTypePerformance]; exists {
		if err := performanceChecker.Configure(perfConfig); err != nil {
			return fmt.Errorf("failed to configure performance checker: %w", err)
		}
	}
	if err := r.RegisterChecker(performanceChecker); err != nil {
		return fmt.Errorf("failed to register performance checker: %w", err)
	}

	// Register File Vibe
	fileChecker := NewFileChecker()
	if fileConfig, exists := config.Vibes[models.VibeTypeFile]; exists {
		if err := fileChecker.Configure(fileConfig); err != nil {
			return fmt.Errorf("failed to configure file checker: %w", err)
		}
	}
	if err := r.RegisterChecker(fileChecker); err != nil {
		return fmt.Errorf("failed to register file checker: %w", err)
	}

	// Register Git Vibe
	gitChecker := NewGitChecker()
	if gitConfig, exists := config.Vibes[models.VibeTypeGit]; exists {
		if err := gitChecker.Configure(gitConfig); err != nil {
			return fmt.Errorf("failed to configure git checker: %w", err)
		}
	}
	if err := r.RegisterChecker(gitChecker); err != nil {
		return fmt.Errorf("failed to register git checker: %w", err)
	}

	// Register Dependency Vibe
	dependencyChecker := NewDependencyChecker()
	if depConfig, exists := config.Vibes[models.VibeTypeDependency]; exists {
		if err := dependencyChecker.Configure(depConfig); err != nil {
			return fmt.Errorf("failed to configure dependency checker: %w", err)
		}
	}
	if err := r.RegisterChecker(dependencyChecker); err != nil {
		return fmt.Errorf("failed to register dependency checker: %w", err)
	}

	// Register Documentation Vibe
	docChecker := NewDocumentationChecker()
	if docConfig, exists := config.Vibes[models.VibeTypeDocumentation]; exists {
		if err := docChecker.Configure(docConfig); err != nil {
			return fmt.Errorf("failed to configure documentation checker: %w", err)
		}
	}
	if err := r.RegisterChecker(docChecker); err != nil {
		return fmt.Errorf("failed to register documentation checker: %w", err)
	}

	return nil
}

// UnregisterChecker removes a vibe checker
func (r *Registry) UnregisterChecker(vibeType models.VibeType) {
	r.mu.Lock()
	defer r.mu.Unlock()

	delete(r.checkers, vibeType)
}

// Clear removes all registered checkers
func (r *Registry) Clear() {
	r.mu.Lock()
	defer r.mu.Unlock()

	r.checkers = make(map[models.VibeType]Checker)
}

// ValidateConfig validates the configuration for all registered checkers
func (r *Registry) ValidateConfig(config *models.Configuration) error {
	r.mu.RLock()
	defer r.mu.RUnlock()

	for vibeType, checker := range r.checkers {
		if vibeConfig, exists := config.Vibes[vibeType]; exists && vibeConfig.Enabled {
			if err := checker.Configure(vibeConfig); err != nil {
				return fmt.Errorf("invalid configuration for %s: %w", vibeType, err)
			}
		}
	}

	return nil
}
