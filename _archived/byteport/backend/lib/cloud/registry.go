package cloud

import (
	"fmt"
	"sync"
)

// registry is the global provider registry
var (
	globalRegistry *providerRegistry
	registryOnce   sync.Once
)

// providerRegistry implements ProviderRegistry
type providerRegistry struct {
	mu        sync.RWMutex
	providers map[string]registeredProvider
}

// registeredProvider holds provider metadata and factory
type registeredProvider struct {
	metadata ProviderMetadata
	factory  ProviderFactory
}

// GetRegistry returns the global provider registry (singleton)
func GetRegistry() ProviderRegistry {
	registryOnce.Do(func() {
		globalRegistry = &providerRegistry{
			providers: make(map[string]registeredProvider),
		}
	})
	return globalRegistry
}

// Register adds a provider to the registry
func (r *providerRegistry) Register(metadata ProviderMetadata, factory ProviderFactory) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	if metadata.Name == "" {
		return &ValidationError{
			CloudError: &CloudError{
				Category:  ErrorCategoryValidation,
				Code:      "INVALID_METADATA",
				Message:   "Provider name cannot be empty",
				Retryable: false,
			},
		}
	}

	if factory == nil {
		return &ValidationError{
			CloudError: &CloudError{
				Category:  ErrorCategoryValidation,
				Code:      "INVALID_FACTORY",
				Message:   "Provider factory cannot be nil",
				Retryable: false,
			},
		}
	}

	if _, exists := r.providers[metadata.Name]; exists {
		return &ConflictError{
			CloudError: &CloudError{
				Category:  ErrorCategoryConflict,
				Code:      "PROVIDER_EXISTS",
				Message:   fmt.Sprintf("Provider '%s' is already registered", metadata.Name),
				Retryable: false,
			},
			ConflictingResource: metadata.Name,
		}
	}

	r.providers[metadata.Name] = registeredProvider{
		metadata: metadata,
		factory:  factory,
	}

	return nil
}

// Unregister removes a provider from the registry
func (r *providerRegistry) Unregister(providerName string) error {
	r.mu.Lock()
	defer r.mu.Unlock()

	if _, exists := r.providers[providerName]; !exists {
		return &ResourceNotFoundError{
			CloudError: &CloudError{
				Category:   ErrorCategoryNotFound,
				Code:       "PROVIDER_NOT_FOUND",
				Message:    fmt.Sprintf("Provider '%s' not found in registry", providerName),
				ResourceID: providerName,
				Retryable:  false,
			},
		}
	}

	delete(r.providers, providerName)
	return nil
}

// Get creates a provider instance with the given credentials
func (r *providerRegistry) Get(providerName string, credentials Credentials) (CloudProvider, error) {
	r.mu.RLock()
	registered, exists := r.providers[providerName]
	r.mu.RUnlock()

	if !exists {
		return nil, &ResourceNotFoundError{
			CloudError: &CloudError{
				Category:   ErrorCategoryNotFound,
				Code:       "PROVIDER_NOT_FOUND",
				Message:    fmt.Sprintf("Provider '%s' not found in registry", providerName),
				ResourceID: providerName,
				Retryable:  false,
			},
		}
	}

	provider, err := registered.factory(credentials)
	if err != nil {
		return nil, fmt.Errorf("failed to create provider '%s': %w", providerName, err)
	}

	return provider, nil
}

// List returns metadata for all registered providers
func (r *providerRegistry) List() []ProviderMetadata {
	r.mu.RLock()
	defer r.mu.RUnlock()

	metadataList := make([]ProviderMetadata, 0, len(r.providers))
	for _, registered := range r.providers {
		metadataList = append(metadataList, registered.metadata)
	}

	return metadataList
}

// Supports checks if a provider supports a specific resource type
func (r *providerRegistry) Supports(providerName string, resourceType ResourceType) bool {
	r.mu.RLock()
	registered, exists := r.providers[providerName]
	r.mu.RUnlock()

	if !exists {
		return false
	}

	for _, supportedType := range registered.metadata.SupportedResources {
		if supportedType == resourceType {
			return true
		}
	}

	return false
}

// GetMetadata retrieves metadata for a specific provider
func (r *providerRegistry) GetMetadata(providerName string) (*ProviderMetadata, error) {
	r.mu.RLock()
	registered, exists := r.providers[providerName]
	r.mu.RUnlock()

	if !exists {
		return nil, &ResourceNotFoundError{
			CloudError: &CloudError{
				Category:   ErrorCategoryNotFound,
				Code:       "PROVIDER_NOT_FOUND",
				Message:    fmt.Sprintf("Provider '%s' not found in registry", providerName),
				ResourceID: providerName,
				Retryable:  false,
			},
		}
	}

	return &registered.metadata, nil
}

// MustRegister registers a provider and panics on error (for init-time registration)
func MustRegister(metadata ProviderMetadata, factory ProviderFactory) {
	if err := GetRegistry().Register(metadata, factory); err != nil {
		panic(fmt.Sprintf("failed to register provider '%s': %v", metadata.Name, err))
	}
}

// ProviderExists checks if a provider is registered
func ProviderExists(providerName string) bool {
	reg := globalRegistry
	if reg == nil {
		return false
	}

	reg.mu.RLock()
	defer reg.mu.RUnlock()

	_, exists := reg.providers[providerName]
	return exists
}

// GetSupportedProviders returns a list of provider names that support a resource type
func GetSupportedProviders(resourceType ResourceType) []string {
	reg := GetRegistry()
	allProviders := reg.List()

	supported := make([]string, 0)
	for _, metadata := range allProviders {
		for _, supportedType := range metadata.SupportedResources {
			if supportedType == resourceType {
				supported = append(supported, metadata.Name)
				break
			}
		}
	}

	return supported
}

// ProviderInfo provides detailed information about a registered provider
type ProviderInfo struct {
	Metadata      ProviderMetadata `json:"metadata"`
	IsRegistered  bool             `json:"is_registered"`
	ResourceTypes []ResourceType   `json:"resource_types"`
	Capabilities  []Capability     `json:"capabilities"`
}

// GetProviderInfo retrieves detailed information about a provider
func GetProviderInfo(providerName string) (*ProviderInfo, error) {
	reg := GetRegistry()
	metadata, err := reg.GetMetadata(providerName)
	if err != nil {
		return nil, err
	}

	return &ProviderInfo{
		Metadata:      *metadata,
		IsRegistered:  true,
		ResourceTypes: metadata.SupportedResources,
		Capabilities:  metadata.Capabilities,
	}, nil
}
