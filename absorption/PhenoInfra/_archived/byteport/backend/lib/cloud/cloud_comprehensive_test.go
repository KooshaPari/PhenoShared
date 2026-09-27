package cloud

import (
	"context"
	"errors"
	"testing"
	"time"
)

// Test Error constructors and methods
func TestCloudError_Error(t *testing.T) {
	err := &CloudError{
		Category: ErrorCategoryAuthentication,
		Code:     "AUTH_001",
		Message:  "Invalid credentials",
		Provider: "aws",
	}

	expected := "[aws/AUTHENTICATION] AUTH_001: Invalid credentials"
	if err.Error() != expected {
		t.Errorf("Expected '%s', got '%s'", expected, err.Error())
	}

	// Test without provider
	err2 := &CloudError{
		Category: ErrorCategoryValidation,
		Code:     "VAL_001",
		Message:  "Invalid config",
	}

	expected2 := "[VALIDATION] VAL_001: Invalid config"
	if err2.Error() != expected2 {
		t.Errorf("Expected '%s', got '%s'", expected2, err2.Error())
	}
}

func TestAuthenticationError(t *testing.T) {
	cause := errors.New("http 401")
	authErr := NewAuthenticationError("aws", "Invalid API key", cause)

	if authErr.CloudError.Category != ErrorCategoryAuthentication {
		t.Error("Expected AUTHENTICATION category")
	}
	if authErr.CloudError.Code != "AUTH_FAILED" {
		t.Error("Expected AUTH_FAILED code")
	}
	if authErr.CloudError.Retryable {
		t.Error("Expected non-retryable")
	}
	if authErr.CloudError.Cause != cause {
		t.Error("Expected cause to be set")
	}
}

func TestQuotaError(t *testing.T) {
	resetTime := time.Now().Add(time.Hour)
	quotaErr := NewQuotaError("gcp", "Rate limit exceeded", 100, 101, resetTime)

	if quotaErr.CloudError.Category != ErrorCategoryQuota {
		t.Error("Expected QUOTA category")
	}
	if quotaErr.Limit != 100 {
		t.Errorf("Expected limit 100, got %d", quotaErr.Limit)
	}
	if quotaErr.Current != 101 {
		t.Errorf("Expected current 101, got %d", quotaErr.Current)
	}
	if !quotaErr.CloudError.Retryable {
		t.Error("Expected retryable")
	}
}

func TestConflictError(t *testing.T) {
	conflictErr := NewConflictError("azure", "Resource already exists", "my-resource")

	if conflictErr.CloudError.Category != ErrorCategoryConflict {
		t.Error("Expected CONFLICT category")
	}
	if conflictErr.ConflictingResource != "my-resource" {
		t.Error("Expected conflicting resource to be set")
	}
	if conflictErr.CloudError.Retryable {
		t.Error("Expected non-retryable")
	}
}

func TestInternalProviderError(t *testing.T) {
	cause := errors.New("internal server error")
	internalErr := NewInternalProviderError("aws", "Service unavailable", 500, cause)

	if internalErr.CloudError.Category != ErrorCategoryInternal {
		t.Error("Expected INTERNAL category")
	}
	if internalErr.CloudError.StatusCode != 500 {
		t.Errorf("Expected status code 500, got %d", internalErr.CloudError.StatusCode)
	}
	if !internalErr.CloudError.Retryable {
		t.Error("Expected retryable")
	}
}

func TestWrapError(t *testing.T) {
	originalErr := errors.New("connection failed")
	wrappedErr := WrapError("aws", ErrorCategoryNetwork, "Network timeout", originalErr)

	if wrappedErr.Category != ErrorCategoryNetwork {
		t.Error("Expected NETWORK category")
	}
	if wrappedErr.Cause != originalErr {
		t.Error("Expected cause to be original error")
	}
	if !wrappedErr.Retryable {
		t.Error("Expected retryable for network error")
	}
}

func TestShouldRetry_NetworkError(t *testing.T) {
	networkErr := NewNetworkError("aws", "https://api.aws.com", "Timeout", nil)
	
	if !ShouldRetry(networkErr, DefaultRetryConfig) {
		t.Error("Expected network error to be retryable")
	}
}

func TestShouldRetry_QuotaError(t *testing.T) {
	quotaErr := NewQuotaError("gcp", "Rate limit", 100, 101, time.Now().Add(time.Hour))
	
	if !ShouldRetry(quotaErr, DefaultRetryConfig) {
		t.Error("Expected quota error to be retryable")
	}
}

func TestShouldRetry_ProvisioningError(t *testing.T) {
	provErr := NewProvisioningError("azure", "building", "Build failed", nil)
	
	if !ShouldRetry(provErr, DefaultRetryConfig) {
		t.Error("Expected provisioning error to be retryable")
	}
}

func TestShouldRetry_InternalError(t *testing.T) {
	internalErr := NewInternalProviderError("aws", "Server error", 500, nil)
	
	if !ShouldRetry(internalErr, DefaultRetryConfig) {
		t.Error("Expected internal error to be retryable")
	}
}

func TestShouldRetry_NonRetryable(t *testing.T) {
	authErr := NewAuthenticationError("aws", "Invalid key", nil)
	
	if ShouldRetry(authErr, DefaultRetryConfig) {
		t.Error("Expected authentication error to not be retryable")
	}
}

func TestShouldRetry_Timeout(t *testing.T) {
	if !ShouldRetry(ErrTimeout, DefaultRetryConfig) {
		t.Error("Expected timeout error to be retryable")
	}

	if !ShouldRetry(context.DeadlineExceeded, DefaultRetryConfig) {
		t.Error("Expected deadline exceeded to be retryable")
	}
}

func TestShouldRetry_NilError(t *testing.T) {
	if ShouldRetry(nil, DefaultRetryConfig) {
		t.Error("Expected nil error to not be retryable")
	}
}

func TestCalculateBackoff(t *testing.T) {
	config := RetryConfig{
		MaxRetries:   5,
		InitialDelay: 1 * time.Second,
		MaxDelay:     16 * time.Second,
		Multiplier:   2.0,
		Jitter:       false,
	}

	// Test increasing delays
	delay0 := CalculateBackoff(0, config)
	if delay0 != 1*time.Second {
		t.Errorf("Expected 1s for attempt 0, got %v", delay0)
	}

	delay1 := CalculateBackoff(1, config)
	if delay1 != 2*time.Second {
		t.Errorf("Expected 2s for attempt 1, got %v", delay1)
	}

	delay2 := CalculateBackoff(2, config)
	if delay2 != 4*time.Second {
		t.Errorf("Expected 4s for attempt 2, got %v", delay2)
	}

	// Test max delay cap
	delay5 := CalculateBackoff(5, config)
	if delay5 != 0 {
		t.Errorf("Expected 0 for attempt >= maxRetries, got %v", delay5)
	}

	// Test jitter (just verify it doesn't crash and produces reasonable values)
	configWithJitter := config
	configWithJitter.Jitter = true
	delayJitter := CalculateBackoff(1, configWithJitter)
	if delayJitter <= 0 || delayJitter > 3*time.Second {
		t.Errorf("Expected reasonable jittered delay, got %v", delayJitter)
	}
}

// Test ExampleProvider
func TestNewExampleProvider(t *testing.T) {
	creds := Credentials{
		Type: "api_key",
		Data: map[string]string{"api_key": "test-key"},
	}

	provider, err := NewExampleProvider(creds)
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	if provider == nil {
		t.Fatal("Expected provider, got nil")
	}

	metadata := provider.GetMetadata()
	if metadata.Name != "example" {
		t.Errorf("Expected provider name 'example', got '%s'", metadata.Name)
	}
}

func TestExampleProvider_SupportsResource(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})

	if !provider.SupportsResource(ResourceTypeComputeContainer) {
		t.Error("Expected to support compute container")
	}

	if provider.SupportsResource(ResourceTypeComputeVM) {
		t.Error("Expected not to support compute VM")
	}
}

func TestExampleProvider_GetCapabilities(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})

	capabilities := provider.GetCapabilities()
	if len(capabilities) == 0 {
		t.Error("Expected non-empty capabilities")
	}
}

func TestExampleProvider_Initialize(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	newCreds := Credentials{
		Type: "oauth",
		Data: map[string]string{"token": "new-token"},
	}

	err := provider.Initialize(ctx, newCreds)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
}

func TestExampleProvider_ValidateCredentials(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	err := provider.ValidateCredentials(ctx)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
}

func TestExampleProvider_CreateResource_UnsupportedType(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	config := ResourceConfig{
		Type:   ResourceTypeComputeVM,
		Name:   "test-vm",
		Region: "us-west-1",
	}

	_, err := provider.CreateResource(ctx, config)
	if err == nil {
		t.Error("Expected error for unsupported resource type")
	}

	var notSupportedErr *NotSupportedError
	if !errors.As(err, &notSupportedErr) {
		t.Errorf("Expected NotSupportedError, got: %T", err)
	}
}

func TestExampleProvider_CreateResource_Container(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	config := ResourceConfig{
		Type:   ResourceTypeComputeContainer,
		Name:   "test-container",
		Region: "us-west-1",
		Tags:   map[string]string{"env": "test"},
	}

	resource, err := provider.CreateResource(ctx, config)
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	if resource == nil {
		t.Fatal("Expected resource, got nil")
	}

	if resource.Name != "test-container" {
		t.Errorf("Expected name 'test-container', got '%s'", resource.Name)
	}

	if resource.Status != DeploymentStateActive {
		t.Errorf("Expected status 'active', got '%s'", resource.Status)
	}
}

func TestExampleProvider_CreateResource_Database(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	config := ResourceConfig{
		Type:   ResourceTypeDatabaseServerless,
		Name:   "test-db",
		Region: "us-west-1",
	}

	_, err := provider.CreateResource(ctx, config)
	if err == nil {
		t.Error("Expected error for database creation (not implemented)")
	}
}

func TestExampleProvider_GetResource(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	_, err := provider.GetResource(ctx, "nonexistent-id")
	if err == nil {
		t.Error("Expected error for nonexistent resource")
	}

	var notFoundErr *ResourceNotFoundError
	if !errors.As(err, &notFoundErr) {
		t.Errorf("Expected ResourceNotFoundError, got: %T", err)
	}
}

func TestExampleProvider_UpdateResource(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	config := ResourceConfig{
		Name: "updated-name",
	}

	_, err := provider.UpdateResource(ctx, "test-id", config)
	if err == nil {
		t.Error("Expected not supported error")
	}
}

func TestExampleProvider_DeleteResource(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	err := provider.DeleteResource(ctx, "test-id")
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
}

func TestExampleProvider_ListResources(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	resources, err := provider.ListResources(ctx, ResourceFilter{})
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}

	if resources == nil {
		t.Error("Expected empty slice, got nil")
	}
}

func TestExampleProvider_Deploy(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	deployConfig := DeploymentConfig{
		ResourceID: "test-resource",
		Version:    "1.0.0",
		Strategy:   "rolling",
	}

	deployment, err := provider.Deploy(ctx, deployConfig)
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	if deployment == nil {
		t.Fatal("Expected deployment, got nil")
	}

	if deployment.State != DeploymentStateDeploying {
		t.Errorf("Expected state 'deploying', got '%s'", deployment.State)
	}
}

func TestExampleProvider_GetDeploymentStatus(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	_, err := provider.GetDeploymentStatus(ctx, "test-id")
	if err == nil {
		t.Error("Expected error for nonexistent deployment")
	}
}

func TestExampleProvider_RollbackDeployment(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	err := provider.RollbackDeployment(ctx, "test-id")
	if err == nil {
		t.Error("Expected not supported error")
	}
}

func TestExampleProvider_GetLogs(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	resource := &Resource{ID: "test-id"}
	_, err := provider.GetLogs(ctx, resource, LogOptions{})
	if err == nil {
		t.Error("Expected not supported error")
	}
}

func TestExampleProvider_GetMetrics(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	resource := &Resource{ID: "test-id"}
	metrics, err := provider.GetMetrics(ctx, resource, MetricOptions{})
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}

	if metrics == nil {
		t.Error("Expected empty slice, got nil")
	}
}

func TestExampleProvider_EstimateCost(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	config := ResourceConfig{
		Type: ResourceTypeComputeContainer,
		Name: "test",
	}

	estimate, err := provider.EstimateCost(ctx, config)
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}

	if estimate == nil {
		t.Fatal("Expected estimate, got nil")
	}

	if estimate.MonthlyUSD <= 0 {
		t.Error("Expected positive monthly cost")
	}
}

func TestExampleProvider_GetActualCost(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	resource := &Resource{ID: "test-id"}
	_, err := provider.GetActualCost(ctx, resource, TimeRange{})
	if err == nil {
		t.Error("Expected not supported error")
	}
}

func TestExampleProvider_SetScale(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	// Cast to Scalable interface
	scalable, ok := provider.(Scalable)
	if !ok {
		t.Fatal("Expected provider to implement Scalable interface")
	}

	err := scalable.SetScale(ctx, "test-id", ScaleConfig{})
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
}

func TestExampleProvider_GetScaleConfig(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	// Cast to Scalable interface
	scalable, ok := provider.(Scalable)
	if !ok {
		t.Fatal("Expected provider to implement Scalable interface")
	}

	_, err := scalable.GetScaleConfig(ctx, "test-id")
	if err == nil {
		t.Error("Expected error for nonexistent resource")
	}
}

func TestExampleProvider_AutoScale(t *testing.T) {
	provider, _ := NewExampleProvider(Credentials{})
	ctx := context.Background()

	// Cast to Scalable interface
	scalable, ok := provider.(Scalable)
	if !ok {
		t.Fatal("Expected provider to implement Scalable interface")
	}

	err := scalable.AutoScale(ctx, "test-id", true)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
}

// Test Registry functions
func TestGetRegistry(t *testing.T) {
	reg1 := GetRegistry()
	reg2 := GetRegistry()

	if reg1 != reg2 {
		t.Error("Expected singleton registry")
	}
}

func TestRegistry_Register(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name:    "test-provider",
		Version: "1.0.0",
	}

	factory := func(creds Credentials) (CloudProvider, error) {
		return NewExampleProvider(creds)
	}

	err := reg.Register(metadata, factory)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}

	// Cleanup
	_ = reg.Unregister("test-provider")
}

func TestRegistry_Register_EmptyName(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name: "",
	}

	err := reg.Register(metadata, nil)
	if err == nil {
		t.Error("Expected error for empty provider name")
	}
}

func TestRegistry_Register_NilFactory(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name: "test",
	}

	err := reg.Register(metadata, nil)
	if err == nil {
		t.Error("Expected error for nil factory")
	}
}

func TestRegistry_Register_Duplicate(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name:    "duplicate-provider",
		Version: "1.0.0",
	}

	factory := func(creds Credentials) (CloudProvider, error) {
		return NewExampleProvider(creds)
	}

	// First registration
	_ = reg.Register(metadata, factory)

	// Second registration should fail
	err := reg.Register(metadata, factory)
	if err == nil {
		t.Error("Expected error for duplicate registration")
	}

	var conflictErr *ConflictError
	if !errors.As(err, &conflictErr) {
		t.Errorf("Expected ConflictError, got: %T", err)
	}

	// Cleanup
	_ = reg.Unregister("duplicate-provider")
}

func TestRegistry_Unregister(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name: "temp-provider",
	}

	factory := func(creds Credentials) (CloudProvider, error) {
		return NewExampleProvider(creds)
	}

	_ = reg.Register(metadata, factory)

	err := reg.Unregister("temp-provider")
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
}

func TestRegistry_Unregister_NotFound(t *testing.T) {
	reg := GetRegistry()

	err := reg.Unregister("nonexistent-provider")
	if err == nil {
		t.Error("Expected error for nonexistent provider")
	}

	var notFoundErr *ResourceNotFoundError
	if !errors.As(err, &notFoundErr) {
		t.Errorf("Expected ResourceNotFoundError, got: %T", err)
	}
}

func TestRegistry_Get(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name: "get-test-provider",
	}

	factory := func(creds Credentials) (CloudProvider, error) {
		return NewExampleProvider(creds)
	}

	_ = reg.Register(metadata, factory)

	creds := Credentials{Type: "api_key"}
	provider, err := reg.Get("get-test-provider", creds)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}

	if provider == nil {
		t.Error("Expected provider, got nil")
	}

	// Cleanup
	_ = reg.Unregister("get-test-provider")
}

func TestRegistry_Get_NotFound(t *testing.T) {
	reg := GetRegistry()

	_, err := reg.Get("nonexistent-provider", Credentials{})
	if err == nil {
		t.Error("Expected error for nonexistent provider")
	}
}

func TestRegistry_List(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name: "list-test-provider",
	}

	factory := func(creds Credentials) (CloudProvider, error) {
		return NewExampleProvider(creds)
	}

	_ = reg.Register(metadata, factory)

	providers := reg.List()
	if len(providers) == 0 {
		t.Error("Expected at least one provider")
	}

	// Cleanup
	_ = reg.Unregister("list-test-provider")
}

func TestRegistry_Supports(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name: "supports-test-provider",
		SupportedResources: []ResourceType{
			ResourceTypeComputeContainer,
		},
	}

	factory := func(creds Credentials) (CloudProvider, error) {
		return NewExampleProvider(creds)
	}

	_ = reg.Register(metadata, factory)

	if !reg.Supports("supports-test-provider", ResourceTypeComputeContainer) {
		t.Error("Expected provider to support container")
	}

	if reg.Supports("supports-test-provider", ResourceTypeComputeVM) {
		t.Error("Expected provider not to support VM")
	}

	if reg.Supports("nonexistent", ResourceTypeComputeContainer) {
		t.Error("Expected false for nonexistent provider")
	}

	// Cleanup
	_ = reg.Unregister("supports-test-provider")
}

func TestRegistry_GetMetadata(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name:    "metadata-test-provider",
		Version: "2.0.0",
	}

	factory := func(creds Credentials) (CloudProvider, error) {
		return NewExampleProvider(creds)
	}

	_ = reg.Register(metadata, factory)

	retrieved, err := reg.GetMetadata("metadata-test-provider")
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}

	if retrieved.Name != "metadata-test-provider" {
		t.Errorf("Expected name 'metadata-test-provider', got '%s'", retrieved.Name)
	}

	// Cleanup
	_ = reg.Unregister("metadata-test-provider")
}

func TestRegistry_GetMetadata_NotFound(t *testing.T) {
	reg := GetRegistry()

	_, err := reg.GetMetadata("nonexistent-provider")
	if err == nil {
		t.Error("Expected error for nonexistent provider")
	}
}

func TestMustRegister_Panic(t *testing.T) {
	defer func() {
		if r := recover(); r == nil {
			t.Error("Expected panic for invalid registration")
		}
	}()

	// This should panic because name is empty
	MustRegister(ProviderMetadata{Name: ""}, nil)
}

func TestProviderExists(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name: "exists-test-provider",
	}

	factory := func(creds Credentials) (CloudProvider, error) {
		return NewExampleProvider(creds)
	}

	_ = reg.Register(metadata, factory)

	if !ProviderExists("exists-test-provider") {
		t.Error("Expected provider to exist")
	}

	if ProviderExists("nonexistent-provider") {
		t.Error("Expected provider not to exist")
	}

	// Cleanup
	_ = reg.Unregister("exists-test-provider")
}

func TestGetSupportedProviders(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name: "supported-test-provider",
		SupportedResources: []ResourceType{
			ResourceTypeComputeContainer,
		},
	}

	factory := func(creds Credentials) (CloudProvider, error) {
		return NewExampleProvider(creds)
	}

	_ = reg.Register(metadata, factory)

	supported := GetSupportedProviders(ResourceTypeComputeContainer)
	found := false
	for _, name := range supported {
		if name == "supported-test-provider" {
			found = true
			break
		}
	}

	if !found {
		t.Error("Expected to find supported provider")
	}

	// Cleanup
	_ = reg.Unregister("supported-test-provider")
}

func TestGetProviderInfo(t *testing.T) {
	reg := GetRegistry()

	metadata := ProviderMetadata{
		Name:    "info-test-provider",
		Version: "3.0.0",
		SupportedResources: []ResourceType{
			ResourceTypeComputeContainer,
		},
		Capabilities: []Capability{
			CapabilityScalable,
		},
	}

	factory := func(creds Credentials) (CloudProvider, error) {
		return NewExampleProvider(creds)
	}

	_ = reg.Register(metadata, factory)

	info, err := GetProviderInfo("info-test-provider")
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}

	if !info.IsRegistered {
		t.Error("Expected IsRegistered to be true")
	}

	if len(info.ResourceTypes) != 1 {
		t.Errorf("Expected 1 resource type, got %d", len(info.ResourceTypes))
	}

	// Cleanup
	_ = reg.Unregister("info-test-provider")
}

func TestGetProviderInfo_NotFound(t *testing.T) {
	_, err := GetProviderInfo("nonexistent-provider")
	if err == nil {
		t.Error("Expected error for nonexistent provider")
	}
}
