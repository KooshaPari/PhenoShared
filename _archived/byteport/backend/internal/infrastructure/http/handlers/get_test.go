package handlers

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	domain "github.com/byteport/api/internal/domain/deployment"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestGetDeployment_Success(t *testing.T) {
	handler, repo, svc := setupTestHandler()

	dep, _ := domain.NewDeployment("test-dep", "test-owner", nil)
	
	repo.On("FindByUUID", mock.Anything, "test-uuid").Return(dep, nil)
	svc.On("CanUserAccessDeployment", mock.Anything, "user-123", "test-uuid").Return(true, nil)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/deployments/test-uuid", nil)
	c.Set("user_uuid", "user-123")
	c.Params = gin.Params{{Key: "uuid", Value: "test-uuid"}}
	
	handler.GetDeployment(c)

	assert.Equal(t, http.StatusOK, w.Code)
	repo.AssertExpectations(t)
	svc.AssertExpectations(t)
}

func TestGetDeployment_NotFound(t *testing.T) {
	handler, repo, _ := setupTestHandler()

	repo.On("FindByUUID", mock.Anything, "nonexistent").Return(nil, nil)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/deployments/nonexistent", nil)
	c.Set("user_uuid", "user-123")
	c.Params = gin.Params{{Key: "uuid", Value: "nonexistent"}}
	
	handler.GetDeployment(c)

	assert.Equal(t, http.StatusNotFound, w.Code)
	repo.AssertExpectations(t)
}

func TestGetDeployment_Unauthorized(t *testing.T) {
	handler, _, _ := setupTestHandler()

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/deployments/test-uuid", nil)
	c.Params = gin.Params{{Key: "uuid", Value: "test-uuid"}}
	
	handler.GetDeployment(c)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestGetDeployment_Forbidden(t *testing.T) {
	handler, repo, svc := setupTestHandler()

	dep, _ := domain.NewDeployment("test-dep", "test-owner", nil)
	
	repo.On("FindByUUID", mock.Anything, "test-uuid").Return(dep, nil)
	svc.On("CanUserAccessDeployment", mock.Anything, "user-123", "test-uuid").Return(false, nil)

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/deployments/test-uuid", nil)
	c.Set("user_uuid", "user-123")
	c.Params = gin.Params{{Key: "uuid", Value: "test-uuid"}}
	
	handler.GetDeployment(c)

	assert.Equal(t, http.StatusForbidden, w.Code)
	repo.AssertExpectations(t)
	svc.AssertExpectations(t)
}

func TestGetDeployment_RepositoryError(t *testing.T) {
	handler, repo, _ := setupTestHandler()

	repo.On("FindByUUID", mock.Anything, "test-uuid").Return(nil, errors.New("database error"))

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/deployments/test-uuid", nil)
	c.Set("user_uuid", "user-123")
	c.Params = gin.Params{{Key: "uuid", Value: "test-uuid"}}
	
	handler.GetDeployment(c)

	assert.Equal(t, http.StatusInternalServerError, w.Code)
	repo.AssertExpectations(t)
}

func TestGetDeployment_AccessCheckError(t *testing.T) {
	handler, repo, svc := setupTestHandler()

	dep, _ := domain.NewDeployment("test-dep", "test-owner", nil)
	
	repo.On("FindByUUID", mock.Anything, "test-uuid").Return(dep, nil)
	svc.On("CanUserAccessDeployment", mock.Anything, "user-123", "test-uuid").Return(false, errors.New("access check failed"))

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/deployments/test-uuid", nil)
	c.Set("user_uuid", "user-123")
	c.Params = gin.Params{{Key: "uuid", Value: "test-uuid"}}
	
	handler.GetDeployment(c)

	assert.Equal(t, http.StatusInternalServerError, w.Code)
	repo.AssertExpectations(t)
	svc.AssertExpectations(t)
}
