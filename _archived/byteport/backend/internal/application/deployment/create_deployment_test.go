package deployment

import (
	"context"
	"errors"
	"testing"

	"github.com/byteport/api/internal/domain/deployment"
)

// MockRepository is a mock implementation of deployment.Repository
type MockRepository struct {
	CreateFunc         func(ctx context.Context, dep *deployment.Deployment) error
	UpdateFunc         func(ctx context.Context, dep *deployment.Deployment) error
	FindByUUIDFunc     func(ctx context.Context, uuid string) (*deployment.Deployment, error)
	FindByOwnerFunc    func(ctx context.Context, owner string) ([]*deployment.Deployment, error)
	FindByStatusFunc   func(ctx context.Context, status deployment.Status) ([]*deployment.Deployment, error)
	ListFunc           func(ctx context.Context, offset, limit int) ([]*deployment.Deployment, error)
	CountFunc          func(ctx context.Context) (int64, error)
	CountByOwnerFunc   func(ctx context.Context, owner string) (int64, error)
}

func (m *MockRepository) Create(ctx context.Context, dep *deployment.Deployment) error {
	if m.CreateFunc != nil {
		return m.CreateFunc(ctx, dep)
	}
	return nil
}

func (m *MockRepository) Update(ctx context.Context, dep *deployment.Deployment) error {
	if m.UpdateFunc != nil {
		return m.UpdateFunc(ctx, dep)
	}
	return nil
}

func (m *MockRepository) Delete(ctx context.Context, uuid string) error {
	return nil
}

func (m *MockRepository) FindByUUID(ctx context.Context, uuid string) (*deployment.Deployment, error) {
	if m.FindByUUIDFunc != nil {
		return m.FindByUUIDFunc(ctx, uuid)
	}
	return nil, deployment.NewDeploymentNotFoundError(uuid)
}

func (m *MockRepository) FindByOwner(ctx context.Context, owner string) ([]*deployment.Deployment, error) {
	if m.FindByOwnerFunc != nil {
		return m.FindByOwnerFunc(ctx, owner)
	}
	return []*deployment.Deployment{}, nil
}

func (m *MockRepository) FindByProject(ctx context.Context, projectUUID string) ([]*deployment.Deployment, error) {
	return []*deployment.Deployment{}, nil
}

func (m *MockRepository) FindByStatus(ctx context.Context, status deployment.Status) ([]*deployment.Deployment, error) {
	if m.FindByStatusFunc != nil {
		return m.FindByStatusFunc(ctx, status)
	}
	return []*deployment.Deployment{}, nil
}

func (m *MockRepository) List(ctx context.Context, offset, limit int) ([]*deployment.Deployment, error) {
	if m.ListFunc != nil {
		return m.ListFunc(ctx, offset, limit)
	}
	return []*deployment.Deployment{}, nil
}

func (m *MockRepository) Count(ctx context.Context) (int64, error) {
	if m.CountFunc != nil {
		return m.CountFunc(ctx)
	}
	return 0, nil
}

func (m *MockRepository) CountByOwner(ctx context.Context, owner string) (int64, error) {
	if m.CountByOwnerFunc != nil {
		return m.CountByOwnerFunc(ctx, owner)
	}
	return 0, nil
}

// MockService is a mock implementation of deployment.Service
type MockService struct {
	ValidateDeploymentFunc        func(ctx context.Context, dep *deployment.Deployment) error
	CanUserAccessDeploymentFunc   func(ctx context.Context, userUUID, deploymentUUID string) (bool, error)
	CalculateEstimatedCostFunc    func(ctx context.Context, dep *deployment.Deployment) (*deployment.CostInfo, error)
	SelectOptimalProviderFunc     func(ctx context.Context, serviceType string, constraints map[string]interface{}) (string, error)
}

func (m *MockService) ValidateDeployment(ctx context.Context, dep *deployment.Deployment) error {
	if m.ValidateDeploymentFunc != nil {
		return m.ValidateDeploymentFunc(ctx, dep)
	}
	return nil
}

func (m *MockService) CanUserAccessDeployment(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
	if m.CanUserAccessDeploymentFunc != nil {
		return m.CanUserAccessDeploymentFunc(ctx, userUUID, deploymentUUID)
	}
	return true, nil
}

func (m *MockService) CalculateEstimatedCost(ctx context.Context, dep *deployment.Deployment) (*deployment.CostInfo, error) {
	if m.CalculateEstimatedCostFunc != nil {
		return m.CalculateEstimatedCostFunc(ctx, dep)
	}
	return &deployment.CostInfo{Monthly: 0, Breakdown: map[string]float64{}}, nil
}

func (m *MockService) SelectOptimalProvider(ctx context.Context, serviceType string, constraints map[string]interface{}) (string, error) {
	if m.SelectOptimalProviderFunc != nil {
		return m.SelectOptimalProviderFunc(ctx, serviceType, constraints)
	}
	return "default", nil
}

// TestCreateDeploymentUseCase_Execute_Success tests successful deployment creation
func TestCreateDeploymentUseCase_Execute_Success(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{
		CreateFunc: func(ctx context.Context, dep *deployment.Deployment) error {
			return nil
		},
		FindByOwnerFunc: func(ctx context.Context, owner string) ([]*deployment.Deployment, error) {
			return []*deployment.Deployment{}, nil // No existing deployments
		},
	}
	
	mockService := &MockService{
		ValidateDeploymentFunc: func(ctx context.Context, dep *deployment.Deployment) error {
			return nil
		},
	}
	
	useCase := NewCreateDeploymentUseCase(mockRepo, mockService)
	
	req := CreateDeploymentRequest{
		Name:  "test-deployment",
		Owner: "user-123",
		EnvVars: map[string]string{
			"NODE_ENV": "production",
			"PORT":     "3000",
		},
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	if resp.Name != req.Name {
		t.Errorf("Expected name %s, got %s", req.Name, resp.Name)
	}
	
	if resp.Owner != req.Owner {
		t.Errorf("Expected owner %s, got %s", req.Owner, resp.Owner)
	}
	
	if resp.Status != "pending" {
		t.Errorf("Expected status 'pending', got %s", resp.Status)
	}
	
	if resp.UUID == "" {
		t.Error("Expected UUID to be set")
	}
	
	if resp.Message == "" {
		t.Error("Expected message to be set")
	}
}

// TestCreateDeploymentUseCase_Execute_MissingName tests validation error for missing name
func TestCreateDeploymentUseCase_Execute_MissingName(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{}
	mockService := &MockService{}
	
	useCase := NewCreateDeploymentUseCase(mockRepo, mockService)
	
	req := CreateDeploymentRequest{
		Name:  "", // Missing name
		Owner: "user-123",
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err == nil {
		t.Fatal("Expected validation error, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	if appErr != nil && appErr.Message != "deployment name is required" {
		t.Errorf("Expected specific message, got: %s", appErr.Message)
	}
	
	if appErr != nil && appErr.Code != "VALIDATION_ERROR" {
		t.Errorf("Expected VALIDATION_ERROR code, got: %s", appErr.Code)
	}
}

// TestCreateDeploymentUseCase_Execute_MissingOwner tests validation error for missing owner
func TestCreateDeploymentUseCase_Execute_MissingOwner(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{}
	mockService := &MockService{}
	
	useCase := NewCreateDeploymentUseCase(mockRepo, mockService)
	
	req := CreateDeploymentRequest{
		Name:  "test-deployment",
		Owner: "", // Missing owner
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err == nil {
		t.Fatal("Expected validation error, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	if appErr != nil && appErr.Message != "owner is required" {
		t.Errorf("Expected specific message, got: %s", appErr.Message)
	}
	
	if appErr != nil && appErr.Code != "VALIDATION_ERROR" {
		t.Errorf("Expected VALIDATION_ERROR code, got: %s", appErr.Code)
	}
}

// TestCreateDeploymentUseCase_Execute_ValidationError tests domain validation failure
func TestCreateDeploymentUseCase_Execute_ValidationError(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{
		FindByOwnerFunc: func(ctx context.Context, owner string) ([]*deployment.Deployment, error) {
			return []*deployment.Deployment{}, nil
		},
	}
	
	mockService := &MockService{
		ValidateDeploymentFunc: func(ctx context.Context, dep *deployment.Deployment) error {
			return errors.New("invalid deployment configuration")
		},
	}
	
	useCase := NewCreateDeploymentUseCase(mockRepo, mockService)
	
	req := CreateDeploymentRequest{
		Name:  "test-deployment",
		Owner: "user-123",
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err == nil {
		t.Fatal("Expected conflict error, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	if appErr != nil && appErr.Message != "invalid deployment configuration" {
		t.Errorf("Expected specific message, got: %s", appErr.Message)
	}
	
	if appErr != nil && appErr.Code != "CONFLICT" {
		t.Errorf("Expected CONFLICT code, got: %s", appErr.Code)
	}
}

// TestCreateDeploymentUseCase_Execute_RepositoryError tests repository failure
func TestCreateDeploymentUseCase_Execute_RepositoryError(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{
		CreateFunc: func(ctx context.Context, dep *deployment.Deployment) error {
			return errors.New("database connection failed")
		},
		FindByOwnerFunc: func(ctx context.Context, owner string) ([]*deployment.Deployment, error) {
			return []*deployment.Deployment{}, nil
		},
	}
	
	mockService := &MockService{
		ValidateDeploymentFunc: func(ctx context.Context, dep *deployment.Deployment) error {
			return nil
		},
	}
	
	useCase := NewCreateDeploymentUseCase(mockRepo, mockService)
	
	req := CreateDeploymentRequest{
		Name:  "test-deployment",
		Owner: "user-123",
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err == nil {
		t.Fatal("Expected internal error, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	if appErr != nil && appErr.Message != "failed to create deployment" {
		t.Errorf("Expected specific message, got: %s", appErr.Message)
	}
	
	if appErr != nil && appErr.Code != "INTERNAL_ERROR" {
		t.Errorf("Expected INTERNAL_ERROR code, got: %s", appErr.Code)
	}
}

// TestCreateDeploymentUseCase_Execute_WithEnvVars tests deployment with environment variables
func TestCreateDeploymentUseCase_Execute_WithEnvVars(t *testing.T) {
	ctx := context.Background()
	
	var capturedDeployment *deployment.Deployment
	
	mockRepo := &MockRepository{
		CreateFunc: func(ctx context.Context, dep *deployment.Deployment) error {
			capturedDeployment = dep
			return nil
		},
		FindByOwnerFunc: func(ctx context.Context, owner string) ([]*deployment.Deployment, error) {
			return []*deployment.Deployment{}, nil
		},
	}
	
	mockService := &MockService{}
	
	useCase := NewCreateDeploymentUseCase(mockRepo, mockService)
	
	envVars := map[string]string{
		"NODE_ENV":    "production",
		"PORT":        "3000",
		"API_KEY":     "secret",
		"DATABASE_URL": "postgres://localhost",
	}
	
	req := CreateDeploymentRequest{
		Name:    "test-deployment",
		Owner:   "user-123",
		EnvVars: envVars,
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	if capturedDeployment == nil {
		t.Fatal("Expected deployment to be captured")
	}
	
	// Verify all env vars were set
	depEnvVars := capturedDeployment.EnvVars()
	if len(depEnvVars) != len(envVars) {
		t.Errorf("Expected %d env vars, got %d", len(envVars), len(depEnvVars))
	}
	
	for key, expectedValue := range envVars {
		if actualValue, exists := depEnvVars[key]; !exists {
			t.Errorf("Expected env var %s to exist", key)
		} else if actualValue != expectedValue {
			t.Errorf("Expected env var %s=%s, got %s", key, expectedValue, actualValue)
		}
	}
}

// TestCreateDeploymentUseCase_Execute_WithoutEnvVars tests deployment without environment variables
func TestCreateDeploymentUseCase_Execute_WithoutEnvVars(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{
		CreateFunc: func(ctx context.Context, dep *deployment.Deployment) error {
			return nil
		},
	}
	
	mockService := &MockService{
		ValidateDeploymentFunc: func(ctx context.Context, dep *deployment.Deployment) error {
			return nil
		},
	}
	
	useCase := NewCreateDeploymentUseCase(mockRepo, mockService)
	
	req := CreateDeploymentRequest{
		Name:    "test-deployment",
		Owner:   "user-123",
		EnvVars: nil, // No environment variables
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	if resp.Name != req.Name {
		t.Errorf("Expected name %s, got %s", req.Name, resp.Name)
	}
}

// TestCreateDeploymentUseCase_Execute_WithProjectUUID tests deployment with project association
func TestCreateDeploymentUseCase_Execute_WithProjectUUID(t *testing.T) {
	ctx := context.Background()
	
	var capturedDeployment *deployment.Deployment
	
	mockRepo := &MockRepository{
		CreateFunc: func(ctx context.Context, dep *deployment.Deployment) error {
			capturedDeployment = dep
			return nil
		},
		FindByOwnerFunc: func(ctx context.Context, owner string) ([]*deployment.Deployment, error) {
			return []*deployment.Deployment{}, nil
		},
	}
	
	mockService := &MockService{}
	
	useCase := NewCreateDeploymentUseCase(mockRepo, mockService)
	
	projectUUID := "project-456"
	req := CreateDeploymentRequest{
		Name:        "test-deployment",
		Owner:       "user-123",
		ProjectUUID: &projectUUID,
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	if capturedDeployment == nil {
		t.Fatal("Expected deployment to be captured")
	}
	
	if capturedDeployment.ProjectUUID() == nil {
		t.Error("Expected project UUID to be set")
	} else if *capturedDeployment.ProjectUUID() != projectUUID {
		t.Errorf("Expected project UUID %s, got %s", projectUUID, *capturedDeployment.ProjectUUID())
	}
}
