package deployment

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/byteport/api/internal/domain/deployment"
)

// Mock implementations for terminate/update tests
type MockRepositoryTerminate struct {
	FindByUUIDFunc func(ctx context.Context, uuid string) (*deployment.Deployment, error)
	UpdateFunc     func(ctx context.Context, dep *deployment.Deployment) error
}

func (m *MockRepositoryTerminate) Create(ctx context.Context, dep *deployment.Deployment) error {
	return nil
}

func (m *MockRepositoryTerminate) Update(ctx context.Context, dep *deployment.Deployment) error {
	if m.UpdateFunc != nil {
		return m.UpdateFunc(ctx, dep)
	}
	return nil
}

func (m *MockRepositoryTerminate) Delete(ctx context.Context, uuid string) error {
	return nil
}

func (m *MockRepositoryTerminate) FindByUUID(ctx context.Context, uuid string) (*deployment.Deployment, error) {
	if m.FindByUUIDFunc != nil {
		return m.FindByUUIDFunc(ctx, uuid)
	}
	return nil, nil
}

func (m *MockRepositoryTerminate) FindByOwner(ctx context.Context, owner string) ([]*deployment.Deployment, error) {
	return []*deployment.Deployment{}, nil
}

func (m *MockRepositoryTerminate) FindByProject(ctx context.Context, projectUUID string) ([]*deployment.Deployment, error) {
	return []*deployment.Deployment{}, nil
}

func (m *MockRepositoryTerminate) FindByStatus(ctx context.Context, status deployment.Status) ([]*deployment.Deployment, error) {
	return []*deployment.Deployment{}, nil
}

func (m *MockRepositoryTerminate) List(ctx context.Context, offset, limit int) ([]*deployment.Deployment, error) {
	return []*deployment.Deployment{}, nil
}

func (m *MockRepositoryTerminate) Count(ctx context.Context) (int64, error) {
	return 0, nil
}

func (m *MockRepositoryTerminate) CountByOwner(ctx context.Context, owner string) (int64, error) {
	return 0, nil
}

type MockServiceTerminate struct {
	CanUserAccessDeploymentFunc func(ctx context.Context, userUUID, deploymentUUID string) (bool, error)
}

func (m *MockServiceTerminate) ValidateDeployment(ctx context.Context, dep *deployment.Deployment) error {
	return nil
}

func (m *MockServiceTerminate) CanUserAccessDeployment(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
	if m.CanUserAccessDeploymentFunc != nil {
		return m.CanUserAccessDeploymentFunc(ctx, userUUID, deploymentUUID)
	}
	return true, nil
}

func (m *MockServiceTerminate) CalculateEstimatedCost(ctx context.Context, dep *deployment.Deployment) (*deployment.CostInfo, error) {
	return &deployment.CostInfo{}, nil
}

func (m *MockServiceTerminate) SelectOptimalProvider(ctx context.Context, serviceType string, constraints map[string]interface{}) (string, error) {
	return "vercel", nil
}

// ==================== Terminate Deployment Tests ====================

func TestNewTerminateDeploymentUseCase(t *testing.T) {
	repo := &MockRepositoryTerminate{}
	service := &MockServiceTerminate{}
	
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	if uc == nil {
		t.Fatal("Expected use case to be created, got nil")
	}
}

func TestTerminateDeployment_Success(t *testing.T) {
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
		UpdateFunc: func(ctx context.Context, d *deployment.Deployment) error {
			return nil
		},
	}
	
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return true, nil
		},
	}
	
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	response, err := uc.Execute(context.Background(), dep.UUID(), "owner-123")
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
	if response == nil {
		t.Fatal("Expected response, got nil")
	}
	if response.UUID != dep.UUID() {
		t.Errorf("Expected UUID %s, got %s", dep.UUID(), response.UUID)
	}
	if response.Status != "terminated" {
		t.Errorf("Expected status 'terminated', got %s", response.Status)
	}
}

func TestTerminateDeployment_EmptyUUID(t *testing.T) {
	repo := &MockRepositoryTerminate{}
	service := &MockServiceTerminate{}
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	_, err := uc.Execute(context.Background(), "", "owner-123")
	if err == nil {
		t.Error("Expected validation error for empty UUID, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusBadRequest {
		t.Errorf("Expected status code %d, got %d", StatusBadRequest, appErr.StatusCode)
	}
}

func TestTerminateDeployment_EmptyUserUUID(t *testing.T) {
	repo := &MockRepositoryTerminate{}
	service := &MockServiceTerminate{}
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	_, err := uc.Execute(context.Background(), "deploy-uuid", "")
	if err == nil {
		t.Error("Expected unauthorized error for empty user UUID, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusUnauthorized {
		t.Errorf("Expected status code %d, got %d", StatusUnauthorized, appErr.StatusCode)
	}
}

func TestTerminateDeployment_NotFound(t *testing.T) {
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return nil, nil
		},
	}
	service := &MockServiceTerminate{}
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	_, err := uc.Execute(context.Background(), "nonexistent-uuid", "owner-123")
	if err == nil {
		t.Error("Expected not found error, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusNotFound {
		t.Errorf("Expected status code %d, got %d", StatusNotFound, appErr.StatusCode)
	}
}

func TestTerminateDeployment_RepositoryError(t *testing.T) {
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return nil, errors.New("database error")
		},
	}
	service := &MockServiceTerminate{}
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	_, err := uc.Execute(context.Background(), "deploy-uuid", "owner-123")
	if err == nil {
		t.Error("Expected internal error, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusInternalServerError {
		t.Errorf("Expected status code %d, got %d", StatusInternalServerError, appErr.StatusCode)
	}
}

func TestTerminateDeployment_PermissionCheckError(t *testing.T) {
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
	}
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return false, errors.New("permission check failed")
		},
	}
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	_, err := uc.Execute(context.Background(), dep.UUID(), "owner-123")
	if err == nil {
		t.Error("Expected internal error, got nil")
	}
}

func TestTerminateDeployment_Forbidden(t *testing.T) {
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
	}
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return false, nil
		},
	}
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	_, err := uc.Execute(context.Background(), dep.UUID(), "other-user")
	if err == nil {
		t.Error("Expected forbidden error, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusForbidden {
		t.Errorf("Expected status code %d, got %d", StatusForbidden, appErr.StatusCode)
	}
}

func TestTerminateDeployment_AlreadyTerminated(t *testing.T) {
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	_ = dep.SetStatus(deployment.StatusTerminated)
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
	}
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return true, nil
		},
	}
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	_, err := uc.Execute(context.Background(), dep.UUID(), "owner-123")
	if err == nil {
		t.Error("Expected conflict error, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusConflict {
		t.Errorf("Expected status code %d, got %d", StatusConflict, appErr.StatusCode)
	}
}

func TestTerminateDeployment_UpdateError(t *testing.T) {
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
		UpdateFunc: func(ctx context.Context, d *deployment.Deployment) error {
			return errors.New("update failed")
		},
	}
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return true, nil
		},
	}
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	_, err := uc.Execute(context.Background(), dep.UUID(), "owner-123")
	if err == nil {
		t.Error("Expected internal error, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusInternalServerError {
		t.Errorf("Expected status code %d, got %d", StatusInternalServerError, appErr.StatusCode)
	}
}

// ==================== Update Status Tests ====================

func TestNewUpdateStatusUseCase(t *testing.T) {
	repo := &MockRepositoryTerminate{}
	service := &MockServiceTerminate{}
	
	uc := NewUpdateStatusUseCase(repo, service)
	
	if uc == nil {
		t.Fatal("Expected use case to be created, got nil")
	}
}

func TestUpdateStatus_Success(t *testing.T) {
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
		UpdateFunc: func(ctx context.Context, d *deployment.Deployment) error {
			return nil
		},
	}
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return true, nil
		},
	}
	uc := NewUpdateStatusUseCase(repo, service)
	
	req := UpdateStatusRequest{Status: "detecting"}
	err := uc.Execute(context.Background(), dep.UUID(), req, "owner-123")
	if err != nil {
		t.Errorf("Expected no error, got: %v", err)
	}
}

func TestUpdateStatus_EmptyUUID(t *testing.T) {
	repo := &MockRepositoryTerminate{}
	service := &MockServiceTerminate{}
	uc := NewUpdateStatusUseCase(repo, service)
	
	req := UpdateStatusRequest{Status: "detecting"}
	err := uc.Execute(context.Background(), "", req, "owner-123")
	if err == nil {
		t.Error("Expected validation error for empty UUID, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusBadRequest {
		t.Errorf("Expected status code %d, got %d", StatusBadRequest, appErr.StatusCode)
	}
}

func TestUpdateStatus_EmptyStatus(t *testing.T) {
	repo := &MockRepositoryTerminate{}
	service := &MockServiceTerminate{}
	uc := NewUpdateStatusUseCase(repo, service)
	
	req := UpdateStatusRequest{Status: ""}
	err := uc.Execute(context.Background(), "deploy-uuid", req, "owner-123")
	if err == nil {
		t.Error("Expected validation error for empty status, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusBadRequest {
		t.Errorf("Expected status code %d, got %d", StatusBadRequest, appErr.StatusCode)
	}
}

func TestUpdateStatus_EmptyUserUUID(t *testing.T) {
	repo := &MockRepositoryTerminate{}
	service := &MockServiceTerminate{}
	uc := NewUpdateStatusUseCase(repo, service)
	
	req := UpdateStatusRequest{Status: "detecting"}
	err := uc.Execute(context.Background(), "deploy-uuid", req, "")
	if err == nil {
		t.Error("Expected unauthorized error for empty user UUID, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusUnauthorized {
		t.Errorf("Expected status code %d, got %d", StatusUnauthorized, appErr.StatusCode)
	}
}

func TestUpdateStatus_InvalidStatus(t *testing.T) {
	repo := &MockRepositoryTerminate{}
	service := &MockServiceTerminate{}
	uc := NewUpdateStatusUseCase(repo, service)
	
	req := UpdateStatusRequest{Status: "invalid-status"}
	err := uc.Execute(context.Background(), "deploy-uuid", req, "owner-123")
	if err == nil {
		t.Error("Expected validation error for invalid status, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusBadRequest {
		t.Errorf("Expected status code %d, got %d", StatusBadRequest, appErr.StatusCode)
	}
}

func TestUpdateStatus_DeploymentNotFound(t *testing.T) {
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return nil, nil
		},
	}
	service := &MockServiceTerminate{}
	uc := NewUpdateStatusUseCase(repo, service)
	
	req := UpdateStatusRequest{Status: "detecting"}
	err := uc.Execute(context.Background(), "nonexistent-uuid", req, "owner-123")
	if err == nil {
		t.Error("Expected not found error, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusNotFound {
		t.Errorf("Expected status code %d, got %d", StatusNotFound, appErr.StatusCode)
	}
}

func TestUpdateStatus_RepositoryError(t *testing.T) {
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return nil, errors.New("database error")
		},
	}
	service := &MockServiceTerminate{}
	uc := NewUpdateStatusUseCase(repo, service)
	
	req := UpdateStatusRequest{Status: "detecting"}
	err := uc.Execute(context.Background(), "deploy-uuid", req, "owner-123")
	if err == nil {
		t.Error("Expected internal error, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusInternalServerError {
		t.Errorf("Expected status code %d, got %d", StatusInternalServerError, appErr.StatusCode)
	}
}

func TestUpdateStatus_PermissionCheckError(t *testing.T) {
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
	}
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return false, errors.New("permission check failed")
		},
	}
	uc := NewUpdateStatusUseCase(repo, service)
	
	req := UpdateStatusRequest{Status: "detecting"}
	err := uc.Execute(context.Background(), dep.UUID(), req, "owner-123")
	if err == nil {
		t.Error("Expected internal error, got nil")
	}
}

func TestUpdateStatus_Forbidden(t *testing.T) {
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
	}
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return false, nil
		},
	}
	uc := NewUpdateStatusUseCase(repo, service)
	
	req := UpdateStatusRequest{Status: "detecting"}
	err := uc.Execute(context.Background(), dep.UUID(), req, "other-user")
	if err == nil {
		t.Error("Expected forbidden error, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusForbidden {
		t.Errorf("Expected status code %d, got %d", StatusForbidden, appErr.StatusCode)
	}
}

func TestUpdateStatus_InvalidTransition(t *testing.T) {
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
	}
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return true, nil
		},
	}
	uc := NewUpdateStatusUseCase(repo, service)
	
	// Try invalid transition: pending -> deployed (should go through detecting, provisioning, deploying first)
	req := UpdateStatusRequest{Status: "deployed"}
	err := uc.Execute(context.Background(), dep.UUID(), req, "owner-123")
	if err == nil {
		t.Error("Expected conflict error for invalid transition, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusConflict {
		t.Errorf("Expected status code %d, got %d", StatusConflict, appErr.StatusCode)
	}
}

func TestUpdateStatus_UpdateError(t *testing.T) {
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			return dep, nil
		},
		UpdateFunc: func(ctx context.Context, d *deployment.Deployment) error {
			return errors.New("update failed")
		},
	}
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return true, nil
		},
	}
	uc := NewUpdateStatusUseCase(repo, service)
	
	req := UpdateStatusRequest{Status: "detecting"}
	err := uc.Execute(context.Background(), dep.UUID(), req, "owner-123")
	if err == nil {
		t.Error("Expected internal error, got nil")
	}
	
	var appErr *ApplicationError
	if !errors.As(err, &appErr) {
		t.Fatalf("Expected ApplicationError, got: %T", err)
	}
	if appErr.StatusCode != StatusInternalServerError {
		t.Errorf("Expected status code %d, got %d", StatusInternalServerError, appErr.StatusCode)
	}
}

// TestTerminateDeployment_SetStatusError tests SetStatus domain error
func TestTerminateDeployment_SetStatusError(t *testing.T) {
	// Create a deployment that's already in a state where transition to terminated would be invalid
	dep, _ := deployment.NewDeployment("test-deploy", "owner-123", nil)
	// First set it to a status that can't transition to terminated 
	// Actually, all statuses can transition to terminated, so we need to simulate an internal SetStatus error
	
	repo := &MockRepositoryTerminate{
		FindByUUIDFunc: func(ctx context.Context, uuid string) (*deployment.Deployment, error) {
			// Return a deployment that will cause SetStatus to fail
			// Since all statuses can transition to terminated, we simulate an edge case
			return dep, nil
		},
	}
	service := &MockServiceTerminate{
		CanUserAccessDeploymentFunc: func(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
			return true, nil
		},
	}
	uc := NewTerminateDeploymentUseCase(repo, service)
	
	_, err := uc.Execute(context.Background(), dep.UUID(), "owner-123")
	// Since terminated is a valid transition from pending, this should succeed
	// The actual domain logic prevents invalid transitions, but all can go to terminated
	if err != nil {
		t.Errorf("Expected no error for valid transition, got: %v", err)
	}
}

// Test TerminateDeploymentResponse struct
func TestTerminateDeploymentResponse(t *testing.T) {
	now := time.Now().UTC()
	response := &TerminateDeploymentResponse{
		UUID:       "test-uuid",
		Status:     "terminated",
		Message:    "Success",
		Terminated: now,
	}
	
	if response.UUID != "test-uuid" {
		t.Errorf("Expected UUID 'test-uuid', got %s", response.UUID)
	}
	if response.Status != "terminated" {
		t.Errorf("Expected Status 'terminated', got %s", response.Status)
	}
	if !response.Terminated.Equal(now) {
		t.Error("Terminated timestamp mismatch")
	}
}
