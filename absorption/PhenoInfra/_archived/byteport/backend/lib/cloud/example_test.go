package cloud

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestProviderCompliance is a generic test suite that all providers should pass
func TestProviderCompliance(t *testing.T) {
	// Test with mock provider
	provider := newMockProvider()

	t.Run("Metadata", func(t *testing.T) {
		metadata := provider.GetMetadata()
		assert.NotEmpty(t, metadata.Name)
		assert.NotEmpty(t, metadata.Version)
		assert.NotEmpty(t, metadata.SupportedResources)
	})

	t.Run("SupportsResource", func(t *testing.T) {
		metadata := provider.GetMetadata()
		for _, resourceType := range metadata.SupportedResources {
			assert.True(t, provider.SupportsResource(resourceType))
		}

		// Test unsupported resource type
		assert.False(t, provider.SupportsResource("invalid.type"))
	})

	t.Run("CreateAndGetResource", func(t *testing.T) {
		ctx := context.Background()

		config := ResourceConfig{
			Name:     "test-resource",
			Type:     ResourceTypeComputeContainer,
			Provider: "mock",
			Region:   "us-west-1",
			Tags: map[string]string{
				"env": "test",
			},
			Spec: map[string]any{
				"image": "nginx:latest",
			},
		}

		// Create resource
		resource, err := provider.CreateResource(ctx, config)
		require.NoError(t, err)
		assert.Equal(t, config.Name, resource.Name)
		assert.Equal(t, config.Type, resource.Type)

		// Get resource
		fetched, err := provider.GetResource(ctx, resource.ID)
		require.NoError(t, err)
		assert.Equal(t, resource.ID, fetched.ID)
		assert.Equal(t, resource.Name, fetched.Name)
	})

	t.Run("ListResources", func(t *testing.T) {
		ctx := context.Background()

		// Create test resources
		for i := 0; i < 3; i++ {
			_, err := provider.CreateResource(ctx, ResourceConfig{
				Name: "test-" + string(rune(i)),
				Type: ResourceTypeComputeContainer,
			})
			require.NoError(t, err)
		}

		// List all resources
		resources, err := provider.ListResources(ctx, ResourceFilter{})
		require.NoError(t, err)
		assert.GreaterOrEqual(t, len(resources), 3)

		// Filter by type
		resources, err = provider.ListResources(ctx, ResourceFilter{
			Types: []ResourceType{ResourceTypeComputeContainer},
		})
		require.NoError(t, err)
		for _, r := range resources {
			assert.Equal(t, ResourceTypeComputeContainer, r.Type)
		}
	})

	t.Run("DeleteResource", func(t *testing.T) {
		ctx := context.Background()

		// Create resource
		resource, err := provider.CreateResource(ctx, ResourceConfig{
			Name: "delete-me",
			Type: ResourceTypeComputeContainer,
		})
		require.NoError(t, err)

		// Delete resource
		err = provider.DeleteResource(ctx, resource.ID)
		require.NoError(t, err)

		// Verify deletion
		_, err = provider.GetResource(ctx, resource.ID)
		assert.Error(t, err)
		assert.IsType(t, &ResourceNotFoundError{}, err)
	})
}

// TestDeploymentWorkflow tests the deployment state machine
func TestDeploymentWorkflow(t *testing.T) {
	ctx := context.Background()
	provider := newMockProvider()

	// Create resource first
	resource, err := provider.CreateResource(ctx, ResourceConfig{
		Name: "deploy-test",
		Type: ResourceTypeComputeContainer,
	})
	require.NoError(t, err)

	// Deploy
	deployment, err := provider.Deploy(ctx, DeploymentConfig{
		ResourceID: resource.ID,
		Version:    "v1.0.0",
		Source: &DeploymentSource{
			Type:       "git",
			Repository: "https://github.com/example/repo",
			Branch:     "main",
		},
		Strategy: DeploymentStrategyRolling,
	})
	require.NoError(t, err)
	assert.Equal(t, resource.ID, deployment.ResourceID)
	assert.Equal(t, DeploymentStateDeploying, deployment.State)

	// Poll deployment status
	var status *DeploymentStatus
	for i := 0; i < 10; i++ {
		status, err = provider.GetDeploymentStatus(ctx, deployment.ID)
		require.NoError(t, err)

		if status.Deployment.State == DeploymentStateActive {
			break
		}

		time.Sleep(100 * time.Millisecond)
	}

	assert.Equal(t, DeploymentStateActive, status.Deployment.State)
	assert.Equal(t, HealthStatusHealthy, status.Health)
}

// TestErrorHandling tests error scenarios
func TestErrorHandling(t *testing.T) {
	ctx := context.Background()
	provider := newMockProvider()

	t.Run("ResourceNotFound", func(t *testing.T) {
		_, err := provider.GetResource(ctx, "nonexistent")
		assert.Error(t, err)

		var notFoundErr *ResourceNotFoundError
		assert.ErrorAs(t, err, &notFoundErr)
		assert.Equal(t, ErrorCategoryNotFound, notFoundErr.Category)
		assert.False(t, notFoundErr.Retryable)
	})

	t.Run("ValidationError", func(t *testing.T) {
		_, err := provider.CreateResource(ctx, ResourceConfig{
			Name: "", // Invalid: empty name
			Type: ResourceTypeComputeContainer,
		})
		assert.Error(t, err)

		var validationErr *ValidationError
		assert.ErrorAs(t, err, &validationErr)
		assert.Equal(t, ErrorCategoryValidation, validationErr.Category)
	})

	t.Run("NotSupportedError", func(t *testing.T) {
		_, err := provider.CreateResource(ctx, ResourceConfig{
			Name: "test",
			Type: "invalid.type",
		})
		assert.Error(t, err)

		var notSupportedErr *NotSupportedError
		assert.ErrorAs(t, err, &notSupportedErr)
		assert.Equal(t, ErrorCategoryNotSupported, notSupportedErr.Category)
	})
}

// TestRetryLogic tests retry behavior
func TestRetryLogic(t *testing.T) {
	t.Run("ShouldRetry", func(t *testing.T) {
		config := DefaultRetryConfig

		// Network error should be retryable
		networkErr := NewNetworkError("test", "https://api.example.com", "timeout", nil)
		// Verify it's a CloudError with correct category
		assert.Equal(t, ErrorCategoryNetwork, networkErr.Category)
		assert.True(t, networkErr.Retryable)
		// Cast to error interface to test properly
		var netErr error = networkErr
		assert.True(t, ShouldRetry(netErr, config), "Network error should be retryable")

		// Validation error should not be retryable
		validationErr := NewValidationError("test", "name", "invalid name")
		var valErr error = validationErr
		assert.False(t, ShouldRetry(valErr, config))

		// Provisioning error should be retryable
		provisioningErr := NewProvisioningError("test", "deploying", "failed to deploy", nil)
		// Verify it's a CloudError with correct category
		assert.Equal(t, ErrorCategoryProvisioning, provisioningErr.Category)
		assert.True(t, provisioningErr.Retryable)
		// Cast to error interface to test properly
		var provErr error = provisioningErr
		assert.True(t, ShouldRetry(provErr, config), "Provisioning error should be retryable")
	})

	t.Run("CalculateBackoff", func(t *testing.T) {
		config := RetryConfig{
			MaxRetries:   5,
			InitialDelay: 1 * time.Second,
			MaxDelay:     16 * time.Second,
			Multiplier:   2.0,
			Jitter:       false, // Disable jitter for predictable testing
		}

		// Test exponential backoff
		assert.Equal(t, 1*time.Second, CalculateBackoff(0, config))
		assert.Equal(t, 2*time.Second, CalculateBackoff(1, config))
		assert.Equal(t, 4*time.Second, CalculateBackoff(2, config))
		assert.Equal(t, 8*time.Second, CalculateBackoff(3, config))
		assert.Equal(t, 16*time.Second, CalculateBackoff(4, config))

		// Should return 0 when attempt >= MaxRetries
		assert.Equal(t, 0*time.Second, CalculateBackoff(5, config))
		assert.Equal(t, 0*time.Second, CalculateBackoff(10, config))
	})
}

// TestScalability tests scaling operations
func TestScalability(t *testing.T) {
	ctx := context.Background()
	provider := newMockProvider()

	// Create resource
	resource, err := provider.CreateResource(ctx, ResourceConfig{
		Name: "scalable-resource",
		Type: ResourceTypeComputeContainer,
	})
	require.NoError(t, err)

	// Check if provider implements Scalable interface
	scalable, ok := provider.(Scalable)
	if !ok {
		t.Skip("Provider does not implement Scalable interface")
	}

	// Set scale configuration
	scaleConfig := ScaleConfig{
		MinInstances: 2,
		MaxInstances: 10,
		TargetCPU:    intPtr(70),
	}

	err = scalable.SetScale(ctx, resource.ID, scaleConfig)
	require.NoError(t, err)

	// Get scale configuration
	config, err := scalable.GetScaleConfig(ctx, resource.ID)
	require.NoError(t, err)
	assert.Equal(t, 2, config.MinInstances)
	assert.Equal(t, 10, config.MaxInstances)
	assert.Equal(t, 70, *config.TargetCPU)
}

// TestCostEstimation tests cost estimation
func TestCostEstimation(t *testing.T) {
	ctx := context.Background()
	provider := newMockProvider()

	config := ResourceConfig{
		Name: "cost-test",
		Type: ResourceTypeComputeContainer,
		Spec: map[string]any{
			"instance_type": "medium",
			"storage":       "50GB",
		},
	}

	estimate, err := provider.EstimateCost(ctx, config)
	require.NoError(t, err)

	assert.Greater(t, estimate.MonthlyUSD, 0.0)
	assert.NotEmpty(t, estimate.Breakdown)
	assert.Contains(t, []string{"high", "medium", "low"}, estimate.Confidence)
}

// Helper functions

func intPtr(i int) *int {
	return &i
}

// newMockProvider creates a mock provider for testing
func newMockProvider() CloudProvider {
	provider := &MockProvider{
		resources:   make(map[string]*Resource),
		deployments: make(map[string]*Deployment),
	}
	return provider
}

// MockProvider is a simple in-memory provider for testing
type MockProvider struct {
	resources   map[string]*Resource
	deployments map[string]*Deployment
}

func (m *MockProvider) GetMetadata() ProviderMetadata {
	return ProviderMetadata{
		Name:    "mock",
		Version: "1.0.0",
		SupportedResources: []ResourceType{
			ResourceTypeComputeContainer,
			ResourceTypeDatabaseSQL,
		},
		Capabilities: []Capability{
			CapabilityScalable,
			CapabilityLoggable,
		},
		Regions: []Region{
			{ID: "us-west-1", Name: "US West", Location: "California", Available: true},
		},
		AuthTypes:   []string{"mock"},
		Description: "Mock provider for testing",
	}
}

func (m *MockProvider) SupportsResource(resourceType ResourceType) bool {
	metadata := m.GetMetadata()
	for _, t := range metadata.SupportedResources {
		if t == resourceType {
			return true
		}
	}
	return false
}

func (m *MockProvider) GetCapabilities() []Capability {
	return m.GetMetadata().Capabilities
}

func (m *MockProvider) Initialize(ctx context.Context, credentials Credentials) error {
	return nil
}

func (m *MockProvider) ValidateCredentials(ctx context.Context) error {
	return nil
}

func (m *MockProvider) CreateResource(ctx context.Context, config ResourceConfig) (*Resource, error) {
	if config.Name == "" {
		return nil, NewValidationError("mock", "name", "name cannot be empty")
	}

	if !m.SupportsResource(config.Type) {
		return nil, NewNotSupportedError("mock", string(config.Type))
	}

	resource := &Resource{
		ID:           "mock-" + config.Name,
		Name:         config.Name,
		Type:         config.Type,
		Provider:     "mock",
		Region:       config.Region,
		Status:       DeploymentStateActive,
		HealthStatus: HealthStatusHealthy,
		Tags:         config.Tags,
		Metadata:     config.Spec,
		CreatedAt:    time.Now(),
		UpdatedAt:    time.Now(),
	}

	m.resources[resource.ID] = resource
	return resource, nil
}

func (m *MockProvider) GetResource(ctx context.Context, id string) (*Resource, error) {
	resource, exists := m.resources[id]
	if !exists {
		return nil, NewResourceNotFoundError("mock", id)
	}
	return resource, nil
}

func (m *MockProvider) UpdateResource(ctx context.Context, id string, config ResourceConfig) (*Resource, error) {
	resource, exists := m.resources[id]
	if !exists {
		return nil, NewResourceNotFoundError("mock", id)
	}

	resource.Name = config.Name
	resource.Tags = config.Tags
	resource.Metadata = config.Spec
	resource.UpdatedAt = time.Now()

	return resource, nil
}

func (m *MockProvider) DeleteResource(ctx context.Context, id string) error {
	if _, exists := m.resources[id]; !exists {
		return NewResourceNotFoundError("mock", id)
	}
	delete(m.resources, id)
	return nil
}

func (m *MockProvider) ListResources(ctx context.Context, filter ResourceFilter) ([]*Resource, error) {
	resources := make([]*Resource, 0, len(m.resources))

	for _, resource := range m.resources {
		// Apply filters
		if filter.Types != nil {
			matchType := false
			for _, t := range filter.Types {
				if resource.Type == t {
					matchType = true
					break
				}
			}
			if !matchType {
				continue
			}
		}

		resources = append(resources, resource)
	}

	return resources, nil
}

func (m *MockProvider) Deploy(ctx context.Context, config DeploymentConfig) (*Deployment, error) {
	deployment := &Deployment{
		ID:         "deploy-" + config.ResourceID,
		ResourceID: config.ResourceID,
		Version:    config.Version,
		State:      DeploymentStateDeploying, // Start as deploying
		Strategy:   config.Strategy,
		Progress:   0,
		StartedAt:  time.Now(),
		UpdatedAt:  time.Now(),
	}

	m.deployments[deployment.ID] = deployment
	
	// Simulate async deployment completion
	go func() {
		time.Sleep(200 * time.Millisecond)
		deployment.State = DeploymentStateActive
		deployment.Progress = 100
		deployment.UpdatedAt = time.Now()
	}()
	
	return deployment, nil
}

func (m *MockProvider) GetDeploymentStatus(ctx context.Context, id string) (*DeploymentStatus, error) {
	deployment, exists := m.deployments[id]
	if !exists {
		return nil, NewResourceNotFoundError("mock", id)
	}

	return &DeploymentStatus{
		Deployment: deployment,
		Health:     HealthStatusHealthy,
		Instances:  []InstanceInfo{},
	}, nil
}

func (m *MockProvider) RollbackDeployment(ctx context.Context, id string) error {
	return nil
}

func (m *MockProvider) GetLogs(ctx context.Context, resource *Resource, opts LogOptions) (LogStream, error) {
	return nil, NewNotSupportedError("mock", "GetLogs")
}

func (m *MockProvider) GetMetrics(ctx context.Context, resource *Resource, opts MetricOptions) ([]Metric, error) {
	return []Metric{}, nil
}

func (m *MockProvider) EstimateCost(ctx context.Context, config ResourceConfig) (*CostEstimate, error) {
	return &CostEstimate{
		HourlyUSD:  0.10,
		DailyUSD:   2.40,
		MonthlyUSD: 72.00,
		Breakdown: map[string]float64{
			"compute": 50.00,
			"storage": 20.00,
			"network": 2.00,
		},
		Confidence:  "high",
		Currency:    "USD",
		LastUpdated: time.Now(),
	}, nil
}

func (m *MockProvider) GetActualCost(ctx context.Context, resource *Resource, timeRange TimeRange) (*Cost, error) {
	return &Cost{
		TotalUSD: 72.00,
		Breakdown: map[string]float64{
			"compute": 50.00,
			"storage": 20.00,
			"network": 2.00,
		},
		StartTime: timeRange.Start,
		EndTime:   timeRange.End,
		Currency:  "USD",
	}, nil
}

// Implement Scalable interface
func (m *MockProvider) SetScale(ctx context.Context, resourceID string, config ScaleConfig) error {
	return nil
}

func (m *MockProvider) GetScaleConfig(ctx context.Context, resourceID string) (*ScaleConfig, error) {
	return &ScaleConfig{
		MinInstances: 2,
		MaxInstances: 10,
		TargetCPU:    intPtr(70),
	}, nil
}

func (m *MockProvider) AutoScale(ctx context.Context, resourceID string, enabled bool) error {
	return nil
}
