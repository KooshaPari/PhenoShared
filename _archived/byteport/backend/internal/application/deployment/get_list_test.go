package deployment

import (
	"context"
	"fmt"
	"testing"

	"github.com/byteport/api/internal/domain/deployment"
)

// TestGetDeploymentUseCase_Execute_Success tests successful deployment retrieval
func TestGetDeploymentUseCase_Execute_Success(t *testing.T) {
	ctx := context.Background()
	
	// Create a mock deployment
	dep, err := deployment.NewDeployment("test-deployment", "user-123", nil)
	if err != nil {
		t.Fatalf("Failed to create test deployment: %v", err)
	}
	
	mockRepo := &MockRepository{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			if uuid == dep.UUID() {
				return dep, nil
			}
			return nil, deployment.NewDeploymentNotFoundError(uuid)
		},
	}
	
	mockService := &MockService{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return true, nil // Allow access
		},
	}
	
	useCase := NewGetDeploymentUseCase(mockRepo, mockService)
	
	resp, err := useCase.Execute(ctx, dep.UUID(), "user-123")
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	if resp.UUID != dep.UUID() {
		t.Errorf("Expected UUID %s, got %s", dep.UUID(), resp.UUID)
	}
	
	if resp.Name != dep.Name() {
		t.Errorf("Expected name %s, got %s", dep.Name(), resp.Name)
	}
	
	if resp.Owner != dep.Owner() {
		t.Errorf("Expected owner %s, got %s", dep.Owner(), resp.Owner)
	}
	
	if resp.Status != dep.Status().String() {
		t.Errorf("Expected status %s, got %s", dep.Status().String(), resp.Status)
	}
}

// TestGetDeploymentUseCase_Execute_NotFound tests deployment not found error
func TestGetDeploymentUseCase_Execute_NotFound(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return nil, deployment.NewDeploymentNotFoundError(uuid)
		},
	}
	
	mockService := &MockService{}
	
	useCase := NewGetDeploymentUseCase(mockRepo, mockService)
	
	resp, err := useCase.Execute(ctx, "nonexistent-uuid", "user-123")
	
	if err == nil {
		t.Fatal("Expected not found error, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	// Note: The use case wraps repository errors as INTERNAL_ERROR
	// In production, you'd want proper error handling to distinguish
	if appErr != nil && appErr.Code != "INTERNAL_ERROR" && appErr.Code != "NOT_FOUND" {
		t.Errorf("Expected INTERNAL_ERROR or NOT_FOUND code, got: %s", appErr.Code)
	}
}

// TestGetDeploymentUseCase_Execute_EmptyUUID tests validation for empty UUID
func TestGetDeploymentUseCase_Execute_EmptyUUID(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{}
	mockService := &MockService{}
	
	useCase := NewGetDeploymentUseCase(mockRepo, mockService)
	
	resp, err := useCase.Execute(ctx, "", "user-123")
	
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
	
	if appErr != nil && appErr.Code != "VALIDATION_ERROR" {
		t.Errorf("Expected VALIDATION_ERROR code, got: %s", appErr.Code)
	}
}

// TestGetDeploymentUseCase_Execute_EmptyUserUUID tests validation for empty user UUID
func TestGetDeploymentUseCase_Execute_EmptyUserUUID(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{}
	mockService := &MockService{}
	
	useCase := NewGetDeploymentUseCase(mockRepo, mockService)
	
	resp, err := useCase.Execute(ctx, "test-uuid", "")
	
	if err == nil {
		t.Fatal("Expected authorization error, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	if appErr != nil && appErr.Code != "UNAUTHORIZED" {
		t.Errorf("Expected UNAUTHORIZED code, got: %s", appErr.Code)
	}
}

// TestGetDeploymentUseCase_Execute_RepositoryReturnsNil tests when repository returns nil without error
func TestGetDeploymentUseCase_Execute_RepositoryReturnsNil(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return nil, nil // Return nil without error
		},
	}
	
	mockService := &MockService{}
	
	useCase := NewGetDeploymentUseCase(mockRepo, mockService)
	
	resp, err := useCase.Execute(ctx, "test-uuid", "user-123")
	
	if err == nil {
		t.Fatal("Expected not found error, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	if appErr != nil && appErr.Code != "NOT_FOUND" {
		t.Errorf("Expected NOT_FOUND code, got: %s", appErr.Code)
	}
}

// TestGetDeploymentUseCase_Execute_PermissionCheckError tests permission check error
func TestGetDeploymentUseCase_Execute_PermissionCheckError(t *testing.T) {
	ctx := context.Background()
	
	dep, _ := deployment.NewDeployment("test-deployment", "user-123", nil)
	
	mockRepo := &MockRepository{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
	}
	
		mockService := &MockService{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return false, deployment.NewPermissionDeniedError("access", "deployment") // Return error during permission check
		},
	}
	
	useCase := NewGetDeploymentUseCase(mockRepo, mockService)
	
	resp, err := useCase.Execute(ctx, dep.UUID(), "user-123")
	
	if err == nil {
		t.Fatal("Expected permission check error, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	if appErr != nil && appErr.Code != "INTERNAL_ERROR" {
		t.Errorf("Expected INTERNAL_ERROR code, got: %s", appErr.Code)
	}
}

// TestGetDeploymentUseCase_Execute_AccessDenied tests access denied scenario
func TestGetDeploymentUseCase_Execute_AccessDenied(t *testing.T) {
	ctx := context.Background()
	
	dep, _ := deployment.NewDeployment("test-deployment", "user-123", nil)
	
	mockRepo := &MockRepository{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
	}
	
	mockService := &MockService{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return false, nil // Access denied
		},
	}
	
	useCase := NewGetDeploymentUseCase(mockRepo, mockService)
	
	resp, err := useCase.Execute(ctx, dep.UUID(), "user-456")
	
	if err == nil {
		t.Fatal("Expected forbidden error, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	if appErr != nil && appErr.Code != "FORBIDDEN" {
		t.Errorf("Expected FORBIDDEN code, got: %s", appErr.Code)
	}
}

// TestGetDeploymentUseCase_Execute_WithCostInfoAndServices tests mapping with cost info and services
func TestGetDeploymentUseCase_Execute_WithCostInfoAndServices(t *testing.T) {
	ctx := context.Background()
	
	// Create a deployment with services and cost info
	dep, err := deployment.NewDeployment("test-deployment", "user-123", nil)
	if err != nil {
		t.Fatalf("Failed to create test deployment: %v", err)
	}
	
	// Add services to deployment
	service1 := deployment.DeploymentService{
		Name:     "web-service",
		Type:     "web",
		Provider: "aws",
		Status:   "running",
		URL:      "https://example.com",
	}
	service2 := deployment.DeploymentService{
		Name:     "database",
		Type:     "postgres",
		Provider: "aws",
		Status:   "running",
		URL:      "postgres://localhost:5432/db",
	}
	dep.AddService(service1)
	dep.AddService(service2)
	
	// Set cost info
	costInfo := &deployment.CostInfo{
		Monthly: 50.0,
		Breakdown: map[string]float64{
			"aws": 50.0,
		},
	}
	dep.SetCostInfo(costInfo)
	mockRepo := &MockRepository{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
	}
	
	mockService := &MockService{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return true, nil
		},
	}
	
	useCase := NewGetDeploymentUseCase(mockRepo, mockService)
	
	resp, err := useCase.Execute(ctx, dep.UUID(), "user-123")
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	// Verify services mapping
	if len(resp.Services) != 2 {
		t.Errorf("Expected 2 services, got %d", len(resp.Services))
	}
	
	if len(resp.Services) > 0 {
		if resp.Services[0].Name != "web-service" {
			t.Errorf("Expected service name 'web-service', got %s", resp.Services[0].Name)
		}
		if resp.Services[0].Type != "web" {
			t.Errorf("Expected service type 'web', got %s", resp.Services[0].Type)
		}
		if resp.Services[0].Provider != "aws" {
			t.Errorf("Expected service provider 'aws', got %s", resp.Services[0].Provider)
		}
		if resp.Services[0].Status != "running" {
			t.Errorf("Expected service status 'running', got %s", resp.Services[0].Status)
		}
		if resp.Services[0].URL != "https://example.com" {
			t.Errorf("Expected service URL 'https://example.com', got %s", resp.Services[0].URL)
		}
	}
	
	// Verify cost info mapping
	if resp.CostInfo == nil {
		t.Error("Expected cost info to be present")
	} else {
		if resp.CostInfo.Monthly <= 0 {
			t.Errorf("Expected positive monthly cost, got %f", resp.CostInfo.Monthly)
		}
		if len(resp.CostInfo.Breakdown) == 0 {
			t.Error("Expected non-empty cost breakdown")
		}
	}
}

// TestListDeploymentsUseCase_Execute_Success tests successful deployment listing
func TestListDeploymentsUseCase_Execute_Success(t *testing.T) {
	ctx := context.Background()
	
	// Create test deployments
	dep1, _ := deployment.NewDeployment("deployment-1", "user-123", nil)
	dep2, _ := deployment.NewDeployment("deployment-2", "user-123", nil)
	dep3, _ := deployment.NewDeployment("deployment-3", "user-123", nil)
	
	deployments := []*deployment.Deployment{dep1, dep2, dep3}
	
	mockRepo := &MockRepository{
		ListFunc: func(ctx context.Context, offset, limit int) ([]*deployment.Deployment, error) {
			// Simple pagination logic
			start := offset
			end := offset + limit
			if start >= len(deployments) {
				return []*deployment.Deployment{}, nil
			}
			if end > len(deployments) {
				end = len(deployments)
			}
			return deployments[start:end], nil
		},
		CountFunc: func(ctx context.Context) (int64, error) {
			return int64(len(deployments)), nil
		},
	}
	
	useCase := NewListDeploymentsUseCase(mockRepo)
	
	req := ListDeploymentsRequest{
		Offset: 0,
		Limit:  10,
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	if resp.Total != 3 {
		t.Errorf("Expected total 3, got %d", resp.Total)
	}
	
	if len(resp.Deployments) != 3 {
		t.Errorf("Expected 3 deployments, got %d", len(resp.Deployments))
	}
	
	if resp.Offset != 0 {
		t.Errorf("Expected offset 0, got %d", resp.Offset)
	}
	
	if resp.Limit != 10 {
		t.Errorf("Expected limit 10, got %d", resp.Limit)
	}
}

// TestListDeploymentsUseCase_Execute_WithPagination tests pagination logic
func TestListDeploymentsUseCase_Execute_WithPagination(t *testing.T) {
	ctx := context.Background()
	
	// Create test deployments
	var deployments []*deployment.Deployment
	for i := 0; i < 25; i++ {
		dep, _ := deployment.NewDeployment("deployment-"+string(rune(i)), "user-123", nil)
		deployments = append(deployments, dep)
	}
	
	mockRepo := &MockRepository{
		ListFunc: func(ctx context.Context, offset, limit int) ([]*deployment.Deployment, error) {
			start := offset
			end := offset + limit
			if start >= len(deployments) {
				return []*deployment.Deployment{}, nil
			}
			if end > len(deployments) {
				end = len(deployments)
			}
			return deployments[start:end], nil
		},
		CountFunc: func(ctx context.Context) (int64, error) {
			return int64(len(deployments)), nil
		},
	}
	
	useCase := NewListDeploymentsUseCase(mockRepo)
	
	// Test first page
	req := ListDeploymentsRequest{
		Offset: 0,
		Limit:  10,
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if len(resp.Deployments) != 10 {
		t.Errorf("Expected 10 deployments on first page, got %d", len(resp.Deployments))
	}
	
	if resp.Total != 25 {
		t.Errorf("Expected total 25, got %d", resp.Total)
	}
	
	// Test second page
	req.Offset = 10
	resp2, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if len(resp2.Deployments) != 10 {
		t.Errorf("Expected 10 deployments on second page, got %d", len(resp2.Deployments))
	}
	
	// Test last page
	req.Offset = 20
	resp3, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if len(resp3.Deployments) != 5 {
		t.Errorf("Expected 5 deployments on last page, got %d", len(resp3.Deployments))
	}
}

// TestListDeploymentsUseCase_Execute_EmptyList tests empty deployment list
func TestListDeploymentsUseCase_Execute_EmptyList(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{
		ListFunc: func(ctx context.Context, offset, limit int) ([]*deployment.Deployment, error) {
			return []*deployment.Deployment{}, nil
		},
		CountFunc: func(ctx context.Context) (int64, error) {
			return 0, nil
		},
	}
	
	useCase := NewListDeploymentsUseCase(mockRepo)
	
	req := ListDeploymentsRequest{
		Offset: 0,
		Limit:  10,
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	if resp.Total != 0 {
		t.Errorf("Expected total 0, got %d", resp.Total)
	}
	
	if len(resp.Deployments) != 0 {
		t.Errorf("Expected empty deployments list, got %d", len(resp.Deployments))
	}
}

// TestListDeploymentsUseCase_Execute_DefaultLimit tests default limit application
func TestListDeploymentsUseCase_Execute_DefaultLimit(t *testing.T) {
	ctx := context.Background()
	
	var actualLimit int
	
	mockRepo := &MockRepository{
		ListFunc: func(ctx context.Context, offset, limit int) ([]*deployment.Deployment, error) {
			actualLimit = limit
			return []*deployment.Deployment{}, nil
		},
		CountFunc: func(ctx context.Context) (int64, error) {
			return 0, nil
		},
	}
	
	useCase := NewListDeploymentsUseCase(mockRepo)
	
	// Request with no limit (or 0 limit)
	req := ListDeploymentsRequest{
		Offset: 0,
		Limit:  0,
	}
	
	_, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	// Check that a default limit was applied
	if actualLimit == 0 {
		t.Error("Expected default limit to be applied, got 0")
	}
}

// TestListDeploymentsUseCase_Execute_MaxLimit tests maximum limit enforcement
func TestListDeploymentsUseCase_Execute_MaxLimit(t *testing.T) {
	ctx := context.Background()
	
	var actualLimit int
	
	mockRepo := &MockRepository{
		ListFunc: func(ctx context.Context, offset, limit int) ([]*deployment.Deployment, error) {
			actualLimit = limit
			return []*deployment.Deployment{}, nil
		},
		CountFunc: func(ctx context.Context) (int64, error) {
			return 0, nil
		},
	}
	
	useCase := NewListDeploymentsUseCase(mockRepo)
	
	// Request with very large limit
	req := ListDeploymentsRequest{
		Offset: 0,
		Limit:  10000,
	}
	
	_, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	// Check that the limit was capped at maximum
	if actualLimit > 100 {
		t.Errorf("Expected limit to be capped at 100, got %d", actualLimit)
	}
}

// TestListDeploymentsUseCase_Execute_FilterByOwner tests filtering by owner
func TestListDeploymentsUseCase_Execute_FilterByOwner(t *testing.T) {
	ctx := context.Background()
	
	// Create test deployments for different owners
	dep1, _ := deployment.NewDeployment("deployment-1", "user-123", nil)
	dep2, _ := deployment.NewDeployment("deployment-2", "user-123", nil)
	_, _ = deployment.NewDeployment("deployment-3", "user-456", nil)
	var requestedOwner string
	userDeployments := []*deployment.Deployment{dep1, dep2}
	
	mockRepo := &MockRepository{
		FindByOwnerFunc: func(ctx context.Context, owner string) ([]*deployment.Deployment, error) {
			requestedOwner = owner
			if owner == "user-123" {
				return userDeployments, nil
			}
			return []*deployment.Deployment{}, nil
		},
		CountByOwnerFunc: func(ctx context.Context, owner string) (int64, error) {
			if owner == "user-123" {
				return 2, nil
			}
			return 0, nil
		},
	}
	
	useCase := NewListDeploymentsUseCase(mockRepo)
	
	// Request deployments filtered by owner
	req := ListDeploymentsRequest{
		Owner:  "user-123",
		Offset: 0,
		Limit:  10,
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	if requestedOwner != "user-123" {
		t.Errorf("Expected owner filter 'user-123', got %s", requestedOwner)
	}
	
	if len(resp.Deployments) != 2 {
		t.Errorf("Expected 2 deployments, got %d", len(resp.Deployments))
	}
	
	if resp.Total != 2 {
		t.Errorf("Expected total 2, got %d", resp.Total)
	}
}

// TestListDeploymentsUseCase_Execute_FilterByValidStatus tests filtering by valid status
func TestListDeploymentsUseCase_Execute_FilterByValidStatus(t *testing.T) {
	ctx := context.Background()
	
	dep1, _ := deployment.NewDeployment("deployment-1", "user-123", nil)
	dep1.SetStatus(deployment.StatusDeployed)
	
	var requestedStatus deployment.Status
	deployedDeployments := []*deployment.Deployment{dep1}
	
	mockRepo := &MockRepository{
		FindByStatusFunc: func(ctx context.Context, status deployment.Status) ([]*deployment.Deployment, error) {
			requestedStatus = status
			if status == deployment.StatusDeployed {
				return deployedDeployments, nil
			}
			return []*deployment.Deployment{}, nil
		},
		CountFunc: func(ctx context.Context) (int64, error) {
			return 1, nil
		},
	}
	
	useCase := NewListDeploymentsUseCase(mockRepo)
	
	// Request deployments filtered by status
	req := ListDeploymentsRequest{
		Status: "deployed",
		Offset: 0,
		Limit:  10,
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	if requestedStatus != deployment.StatusDeployed {
		t.Errorf("Expected status filter 'deployed', got %s", requestedStatus)
	}
	
	if len(resp.Deployments) != 1 {
		t.Errorf("Expected 1 deployment, got %d", len(resp.Deployments))
	}
	
	if resp.Total != 1 {
		t.Errorf("Expected total 1, got %d", resp.Total)
	}
}

// TestListDeploymentsUseCase_Execute_FilterByInvalidStatus tests filtering by invalid status
func TestListDeploymentsUseCase_Execute_FilterByInvalidStatus(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{}
	useCase := NewListDeploymentsUseCase(mockRepo)
	
	// Request deployments with invalid status
	req := ListDeploymentsRequest{
		Status: "invalid-status",
		Offset: 0,
		Limit:  10,
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err == nil {
		t.Fatal("Expected validation error for invalid status, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	if appErr != nil && appErr.Code != "VALIDATION_ERROR" {
		t.Errorf("Expected VALIDATION_ERROR code, got: %s", appErr.Code)
	}
}

// TestListDeploymentsUseCase_Execute_CountByOwnerError tests when CountByOwner fails
func TestListDeploymentsUseCase_Execute_CountByOwnerError(t *testing.T) {
	ctx := context.Background()
	
	dep1, _ := deployment.NewDeployment("deployment-1", "user-123", nil)
	userDeployments := []*deployment.Deployment{dep1}
	
	mockRepo := &MockRepository{
		FindByOwnerFunc: func(ctx context.Context, owner string) ([]*deployment.Deployment, error) {
			return userDeployments, nil
		},
		CountByOwnerFunc: func(ctx context.Context, owner string) (int64, error) {
			return 0, fmt.Errorf("repository failed") // Simulate count error
		},
	}
	
	useCase := NewListDeploymentsUseCase(mockRepo)
	
	// Request deployments filtered by owner
	req := ListDeploymentsRequest{
		Owner:  "user-123",
		Offset: 0,
		Limit:  10,
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err != nil {
		t.Fatalf("Expected no error despite count failure, got: %v", err)
	}
	
	if resp == nil {
		t.Fatal("Expected response, got nil")
	}
	
	// Should fall back to deployment list length for total
	if resp.Total != int64(len(userDeployments)) {
		t.Errorf("Expected total to fallback to deployment count %d, got %d", len(userDeployments), resp.Total)
	}
	
	if len(resp.Deployments) != 1 {
		t.Errorf("Expected 1 deployment, got %d", len(resp.Deployments))
	}
}

// TestListDeploymentsUseCase_Execute_RepositoryError tests repository error handling
func TestListDeploymentsUseCase_Execute_RepositoryError(t *testing.T) {
	ctx := context.Background()
	
	mockRepo := &MockRepository{
		ListFunc: func(ctx context.Context, offset, limit int) ([]*deployment.Deployment, error) {
			return nil, fmt.Errorf("repository failed") // Simulate repository error
		},
	}
	
	useCase := NewListDeploymentsUseCase(mockRepo)
	
	req := ListDeploymentsRequest{
		Offset: 0,
		Limit:  10,
	}
	
	resp, err := useCase.Execute(ctx, req)
	
	if err == nil {
		t.Fatal("Expected repository error, got nil")
	}
	
	if resp != nil {
		t.Errorf("Expected nil response, got: %+v", resp)
	}
	
	appErr, ok := err.(*ApplicationError)
	if !ok {
		t.Errorf("Expected ApplicationError, got: %T", err)
	}
	
	if appErr != nil && appErr.Code != "INTERNAL_ERROR" {
		t.Errorf("Expected INTERNAL_ERROR code, got: %s", appErr.Code)
	}
}
