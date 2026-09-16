package deployment

import (
	"context"
	"errors"
	"testing"
)

// MockRepository for domain service tests
type MockServiceRepository struct {
	FindByOwnerFunc func(ctx context.Context, ownerUUID string) ([]*Deployment, error)
	FindByUUIDFunc  func(ctx context.Context, uuid string) (*Deployment, error)
}

func (m *MockServiceRepository) Create(ctx context.Context, deployment *Deployment) error {
	return nil
}

func (m *MockServiceRepository) Update(ctx context.Context, deployment *Deployment) error {
	return nil
}

func (m *MockServiceRepository) Delete(ctx context.Context, uuid string) error {
	return nil
}

func (m *MockServiceRepository) FindByUUID(ctx context.Context, uuid string) (*Deployment, error) {
	if m.FindByUUIDFunc != nil {
		return m.FindByUUIDFunc(ctx, uuid)
	}
	return nil, nil
}

func (m *MockServiceRepository) FindByOwner(ctx context.Context, ownerUUID string) ([]*Deployment, error) {
	if m.FindByOwnerFunc != nil {
		return m.FindByOwnerFunc(ctx, ownerUUID)
	}
	return []*Deployment{}, nil
}

func (m *MockServiceRepository) FindByProject(ctx context.Context, projectUUID string) ([]*Deployment, error) {
	return []*Deployment{}, nil
}

func (m *MockServiceRepository) FindByStatus(ctx context.Context, status Status) ([]*Deployment, error) {
	return []*Deployment{}, nil
}

func (m *MockServiceRepository) List(ctx context.Context, offset, limit int) ([]*Deployment, error) {
	return []*Deployment{}, nil
}

func (m *MockServiceRepository) Count(ctx context.Context) (int64, error) {
	return 0, nil
}

func (m *MockServiceRepository) CountByOwner(ctx context.Context, owner string) (int64, error) {
	return 0, nil
}

// TestNewDomainService tests service creation
func TestNewDomainService(t *testing.T) {
	repo := &MockServiceRepository{}
	service := NewDomainService(repo)

	if service == nil {
		t.Fatal("Expected service to be created, got nil")
	}

	// Verify it implements the Service interface
	var _ Service = service
}

// TestValidateDeployment_Success tests successful validation
func TestValidateDeployment_Success(t *testing.T) {
	repo := &MockServiceRepository{
		FindByOwnerFunc: func(ctx context.Context, ownerUUID string) ([]*Deployment, error) {
			return []*Deployment{}, nil // No existing deployments
		},
	}
	service := NewDomainService(repo)

	deployment, err := NewDeployment("test-deploy", "owner-123", nil)
	if err != nil {
		t.Fatalf("Failed to create deployment: %v", err)
	}

	// Add required service
	if err := deployment.AddService(DeploymentService{
		Name:     "web",
		Type:     "frontend",
		Provider: "vercel",
	}); err != nil {
		t.Fatalf("Failed to add service: %v", err)
	}

	err = service.ValidateDeployment(context.Background(), deployment)
	if err != nil {
		t.Errorf("Expected validation to succeed, got error: %v", err)
	}
}

// TestValidateDeployment_NilDeployment tests nil deployment validation
func TestValidateDeployment_NilDeployment(t *testing.T) {
	repo := &MockServiceRepository{}
	service := NewDomainService(repo)

	err := service.ValidateDeployment(context.Background(), nil)
	if err == nil {
		t.Error("Expected error for nil deployment, got nil")
	}
	if err.Error() != "deployment cannot be nil" {
		t.Errorf("Expected 'deployment cannot be nil' error, got: %v", err)
	}
}

// TestValidateDeployment_InvalidDeployment tests invalid deployment validation
func TestValidateDeployment_InvalidDeployment(t *testing.T) {
	repo := &MockServiceRepository{
		FindByOwnerFunc: func(ctx context.Context, ownerUUID string) ([]*Deployment, error) {
			return []*Deployment{}, nil
		},
	}
	service := NewDomainService(repo)

	// Create deployment with invalid data that will fail deployment.Validate()
	deployment := &Deployment{
		uuid:  "", // Empty UUID will cause validation to fail
		name:  "test-name",
		owner: "owner-123",
		status: StatusPending,
	}
	
	err := service.ValidateDeployment(context.Background(), deployment)
	if err == nil {
		t.Error("Expected validation error for invalid deployment, got nil")
	}
	if err.Error() != "deployment UUID cannot be empty" {
		t.Errorf("Expected UUID validation error, got: %v", err)
	}
}

// TestValidateDeployment_NameConflict tests name conflict detection
func TestValidateDeployment_NameConflict(t *testing.T) {
	existingDeployment, _ := NewDeployment("existing-name", "owner-123", nil)
	existingDeployment.uuid = "existing-uuid"
	existingDeployment.AddService(DeploymentService{
		Name:     "web",
		Type:     "frontend",
		Provider: "vercel",
	})

	repo := &MockServiceRepository{
		FindByOwnerFunc: func(ctx context.Context, ownerUUID string) ([]*Deployment, error) {
			return []*Deployment{existingDeployment}, nil
		},
	}
	service := NewDomainService(repo)

	newDeployment, _ := NewDeployment("existing-name", "owner-123", nil)
	newDeployment.uuid = "new-uuid"
	newDeployment.AddService(DeploymentService{
		Name:     "web",
		Type:     "frontend",
		Provider: "vercel",
	})

	err := service.ValidateDeployment(context.Background(), newDeployment)
	if err == nil {
		t.Error("Expected name conflict error, got nil")
	}

	var invErr *DomainError
	if !errors.As(err, &invErr) {
		t.Errorf("Expected DomainError, got: %T", err)
	} else if invErr.Code != "INVALID_DEPLOYMENT" {
		t.Errorf("Expected code 'INVALID_DEPLOYMENT', got: %s", invErr.Code)
	}
}

// TestValidateDeployment_SameDeploymentUpdate tests updating same deployment
func TestValidateDeployment_SameDeploymentUpdate(t *testing.T) {
	existingDeployment, _ := NewDeployment("test-name", "owner-123", nil)
	existingDeployment.uuid = "same-uuid"
	existingDeployment.AddService(DeploymentService{
		Name:     "web",
		Type:     "frontend",
		Provider: "vercel",
	})

	repo := &MockServiceRepository{
		FindByOwnerFunc: func(ctx context.Context, ownerUUID string) ([]*Deployment, error) {
			return []*Deployment{existingDeployment}, nil
		},
	}
	service := NewDomainService(repo)

	// Same deployment with same UUID should pass validation
	err := service.ValidateDeployment(context.Background(), existingDeployment)
	if err != nil {
		t.Errorf("Expected validation to succeed for same deployment, got error: %v", err)
	}
}

// TestValidateDeployment_RepositoryError tests repository error handling

func TestValidateDeployment_RepositoryError(t *testing.T) {
	repositoryErr := errors.New("repository unavailable")
	repo := &MockServiceRepository{
		FindByOwnerFunc: func(ctx context.Context, ownerUUID string) ([]*Deployment, error) {
			return nil, repositoryErr
		},
	}
	service := NewDomainService(repo)

	deployment, _ := NewDeployment("test-deploy", "owner-123", nil)
	deployment.AddService(DeploymentService{
		Name:     "web",
		Type:     "frontend",
		Provider: "vercel",
	})

	err := service.ValidateDeployment(context.Background(), deployment)
	if err == nil {
		t.Error("Expected repository error, got nil")
	} else if err != repositoryErr {
		t.Errorf("Expected repository error, got: %v", err)
	}
}

// Test estimateServiceCost function to get 100% coverage
func TestEstimateServiceCost_AllCases(t *testing.T) {
	tests := []struct {
		name         string
		serviceType  string
		provider     string
		expectedCost float64
	}{
		{
			name:         "valid frontend vercel",
			serviceType:  "frontend",
			provider:     "vercel",
			expectedCost: 0.0,
		},
		{
			name:         "valid backend render",
			serviceType:  "backend", 
			provider:     "render",
			expectedCost: 7.0,
		},
		{
			name:         "valid database supabase",
			serviceType:  "database",
			provider:     "supabase",
			expectedCost: 0.0,
		},
		{
			name:         "valid service type, unknown provider",
			serviceType:  "frontend",
			provider:     "unknown-provider",
			expectedCost: 0.0,
		},
		{
			name:         "unknown service type",
			serviceType:  "unknown-service",
			provider:     "any-provider",
			expectedCost: 0.0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cost := estimateServiceCost(tt.serviceType, tt.provider)
			if cost != tt.expectedCost {
				t.Errorf("Expected cost %f, got %f", tt.expectedCost, cost)
			}
		})
	}
}
func TestCanUserAccessDeployment_Success(t *testing.T) {
	deployment, _ := NewDeployment("test-deploy", "owner-123", nil)
	deployment.uuid = "deploy-uuid"

	repo := &MockServiceRepository{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*Deployment, error) {
			return deployment, nil
		},
	}
	service := NewDomainService(repo)

	canAccess, err := service.CanUserAccessDeployment(context.Background(), "owner-123", "deploy-uuid")
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if !canAccess {
		t.Error("Expected user to have access, got false")
	}
}

// TestCanUserAccessDeployment_NoAccess tests denied access
func TestCanUserAccessDeployment_NoAccess(t *testing.T) {
	deployment, _ := NewDeployment("test-deploy", "owner-123", nil)
	deployment.uuid = "deploy-uuid"

	repo := &MockServiceRepository{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*Deployment, error) {
			return deployment, nil
		},
	}
	service := NewDomainService(repo)

	canAccess, err := service.CanUserAccessDeployment(context.Background(), "other-user", "deploy-uuid")
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if canAccess {
		t.Error("Expected user to not have access, got true")
	}
}

// TestCanUserAccessDeployment_NotFound tests deployment not found
func TestCanUserAccessDeployment_NotFound(t *testing.T) {
	repo := &MockServiceRepository{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*Deployment, error) {
			return nil, nil // Deployment not found
		},
	}
	service := NewDomainService(repo)

	canAccess, err := service.CanUserAccessDeployment(context.Background(), "user-123", "nonexistent-uuid")
	if err == nil {
		t.Error("Expected deployment not found error, got nil")
	}
	if canAccess {
		t.Error("Expected canAccess to be false, got true")
	}

	var notFoundErr *DomainError
	if !errors.As(err, &notFoundErr) {
		t.Errorf("Expected DomainError, got: %T", err)
	} else if notFoundErr.Code != "DEPLOYMENT_NOT_FOUND" {
		t.Errorf("Expected code 'DEPLOYMENT_NOT_FOUND', got: %s", notFoundErr.Code)
	}
}

// TestCanUserAccessDeployment_RepositoryError tests repository error handling
func TestCanUserAccessDeployment_RepositoryError(t *testing.T) {
	repositoryErr := errors.New("repository unavailable")
	repo := &MockServiceRepository{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*Deployment, error) {
			return nil, repositoryErr
		},
	}
	service := NewDomainService(repo)

	canAccess, err := service.CanUserAccessDeployment(context.Background(), "user-123", "deploy-uuid")
	if err == nil {
		t.Error("Expected repository error, got nil")
	}
	if canAccess {
		t.Error("Expected canAccess to be false, got true")
	}
}

// TestCalculateEstimatedCost_Success tests cost calculation
func TestCalculateEstimatedCost_Success(t *testing.T) {
	repo := &MockServiceRepository{}
	service := NewDomainService(repo)

	deployment, _ := NewDeployment("test-deploy", "owner-123", nil)
	deployment.AddService(DeploymentService{
		Name:     "backend",
		Type:     "backend",
		Provider: "render",
	})
	deployment.AddService(DeploymentService{
		Name:     "database",
		Type:     "database",
		Provider: "supabase",
	})

	costInfo, err := service.CalculateEstimatedCost(context.Background(), deployment)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if costInfo == nil {
		t.Fatal("Expected cost info, got nil")
	}

	// Backend render costs $7, supabase free tier = $7 total
	expectedTotal := 7.0
	if costInfo.Monthly != expectedTotal {
		t.Errorf("Expected monthly cost %f, got %f", expectedTotal, costInfo.Monthly)
	}

	if len(costInfo.Breakdown) != 2 {
		t.Errorf("Expected 2 providers in breakdown, got %d", len(costInfo.Breakdown))
	}
}

// TestCalculateEstimatedCost_EmptyServices tests cost with no services
func TestCalculateEstimatedCost_EmptyServices(t *testing.T) {
	repo := &MockServiceRepository{}
	service := NewDomainService(repo)

	deployment, _ := NewDeployment("test-deploy", "owner-123", nil)

	costInfo, err := service.CalculateEstimatedCost(context.Background(), deployment)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if costInfo == nil {
		t.Fatal("Expected cost info, got nil")
	}

	if costInfo.Monthly != 0.0 {
		t.Errorf("Expected monthly cost 0.0, got %f", costInfo.Monthly)
	}

	if len(costInfo.Breakdown) != 0 {
		t.Errorf("Expected empty breakdown, got %d items", len(costInfo.Breakdown))
	}
}

// TestCalculateEstimatedCost_MultipleProviders tests cost with multiple providers
func TestCalculateEstimatedCost_MultipleProviders(t *testing.T) {
	repo := &MockServiceRepository{}
	service := NewDomainService(repo)

	deployment, _ := NewDeployment("test-deploy", "owner-123", nil)
	deployment.AddService(DeploymentService{
		Name:     "api",
		Type:     "backend",
		Provider: "render",
	})
	deployment.AddService(DeploymentService{
		Name:     "worker",
		Type:     "backend",
		Provider: "railway",
	})

	costInfo, err := service.CalculateEstimatedCost(context.Background(), deployment)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	
	// render $7 + railway $5 = $12
	expectedTotal := 12.0
	if costInfo.Monthly != expectedTotal {
		t.Errorf("Expected monthly cost %f, got %f", expectedTotal, costInfo.Monthly)
	}
}

// TestSelectOptimalProvider_Frontend tests provider selection for frontend
func TestSelectOptimalProvider_Frontend(t *testing.T) {
	repo := &MockServiceRepository{}
	service := NewDomainService(repo)

	provider, err := service.SelectOptimalProvider(context.Background(), "frontend", nil)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if provider != "vercel" {
		t.Errorf("Expected provider 'vercel', got '%s'", provider)
	}
}

// TestSelectOptimalProvider_Backend tests provider selection for backend
func TestSelectOptimalProvider_Backend(t *testing.T) {
	repo := &MockServiceRepository{}
	service := NewDomainService(repo)

	provider, err := service.SelectOptimalProvider(context.Background(), "backend", nil)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if provider != "render" {
		t.Errorf("Expected provider 'render', got '%s'", provider)
	}
}

// TestSelectOptimalProvider_Database tests provider selection for database
func TestSelectOptimalProvider_Database(t *testing.T) {
	repo := &MockServiceRepository{}
	service := NewDomainService(repo)

	provider, err := service.SelectOptimalProvider(context.Background(), "database", nil)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if provider != "supabase" {
		t.Errorf("Expected provider 'supabase', got '%s'", provider)
	}
}

// TestSelectOptimalProvider_UnknownType tests provider selection for unknown type
func TestSelectOptimalProvider_UnknownType(t *testing.T) {
	repo := &MockServiceRepository{}
	service := NewDomainService(repo)

	provider, err := service.SelectOptimalProvider(context.Background(), "unknown-type", nil)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if provider != "railway" {
		t.Errorf("Expected default provider 'railway', got '%s'", provider)
	}
}

// TestSelectOptimalProvider_WithConstraints tests provider selection with constraints
func TestSelectOptimalProvider_WithConstraints(t *testing.T) {
	repo := &MockServiceRepository{}
	service := NewDomainService(repo)

	constraints := map[string]interface{}{
		"region": "us-east-1",
		"cost":   "low",
	}

	provider, err := service.SelectOptimalProvider(context.Background(), "backend", constraints)
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if provider != "render" {
		t.Errorf("Expected provider 'render', got '%s'", provider)
	}
}
