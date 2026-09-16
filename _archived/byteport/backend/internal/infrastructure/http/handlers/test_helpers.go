package handlers

import (
	"context"

	"github.com/byteport/api/internal/application/deployment"
	domain "github.com/byteport/api/internal/domain/deployment"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/mock"
)

// mockRepository implements domain.Repository for testing
type mockRepository struct {
	mock.Mock
}

func (m *mockRepository) Create(ctx context.Context, dep *domain.Deployment) error {
	args := m.Called(ctx, dep)
	return args.Error(0)
}

func (m *mockRepository) FindByUUID(ctx context.Context, uuid string) (*domain.Deployment, error) {
	args := m.Called(ctx, uuid)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.Deployment), args.Error(1)
}

func (m *mockRepository) FindByOwner(ctx context.Context, owner string) ([]*domain.Deployment, error) {
	args := m.Called(ctx, owner)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]*domain.Deployment), args.Error(1)
}

func (m *mockRepository) FindByProject(ctx context.Context, projectUUID string) ([]*domain.Deployment, error) {
	args := m.Called(ctx, projectUUID)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]*domain.Deployment), args.Error(1)
}

func (m *mockRepository) FindByStatus(ctx context.Context, status domain.Status) ([]*domain.Deployment, error) {
	args := m.Called(ctx, status)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]*domain.Deployment), args.Error(1)
}

func (m *mockRepository) List(ctx context.Context, offset, limit int) ([]*domain.Deployment, error) {
	args := m.Called(ctx, offset, limit)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]*domain.Deployment), args.Error(1)
}

func (m *mockRepository) Count(ctx context.Context) (int64, error) {
	args := m.Called(ctx)
	return args.Get(0).(int64), args.Error(1)
}

func (m *mockRepository) CountByOwner(ctx context.Context, owner string) (int64, error) {
	args := m.Called(ctx, owner)
	return args.Get(0).(int64), args.Error(1)
}

func (m *mockRepository) Update(ctx context.Context, dep *domain.Deployment) error {
	args := m.Called(ctx, dep)
	return args.Error(0)
}

func (m *mockRepository) Delete(ctx context.Context, uuid string) error {
	args := m.Called(ctx, uuid)
	return args.Error(0)
}

// mockService implements domain.Service for testing
type mockService struct {
	mock.Mock
}

func (m *mockService) ValidateDeployment(ctx context.Context, dep *domain.Deployment) error {
	args := m.Called(ctx, dep)
	return args.Error(0)
}

func (m *mockService) CanUserAccessDeployment(ctx context.Context, userUUID, deploymentUUID string) (bool, error) {
	args := m.Called(ctx, userUUID, deploymentUUID)
	return args.Bool(0), args.Error(1)
}

func (m *mockService) CalculateEstimatedCost(ctx context.Context, dep *domain.Deployment) (*domain.CostInfo, error) {
	args := m.Called(ctx, dep)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*domain.CostInfo), args.Error(1)
}

func (m *mockService) SelectOptimalProvider(ctx context.Context, serviceType string, constraints map[string]interface{}) (string, error) {
	args := m.Called(ctx, serviceType, constraints)
	return args.String(0), args.Error(1)
}

// setupTestRouter creates a test Gin router
func setupTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	return gin.New()
}

// setupTestHandler creates a handler with mocked dependencies
func setupTestHandler() (*DeploymentHandler, *mockRepository, *mockService) {
	repo := new(mockRepository)
	svc := new(mockService)

	createUC := deployment.NewCreateDeploymentUseCase(repo, svc)
	getUC := deployment.NewGetDeploymentUseCase(repo, svc)
	listUC := deployment.NewListDeploymentsUseCase(repo)
	terminateUC := deployment.NewTerminateDeploymentUseCase(repo, svc)
	updateStatusUC := deployment.NewUpdateStatusUseCase(repo, svc)

	handler := NewDeploymentHandler(createUC, getUC, listUC, terminateUC, updateStatusUC)
	return handler, repo, svc
}
