package handlers

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	domain "github.com/byteport/api/internal/domain/deployment"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestListDeployments_Success(t *testing.T) {
	router := setupTestRouter()
	handler, repo, _ := setupTestHandler()

	dep1, _ := domain.NewDeployment("dep-1", "owner-1", nil)
	dep2, _ := domain.NewDeployment("dep-2", "owner-1", nil)
	deployments := []*domain.Deployment{dep1, dep2}

	repo.On("List", mock.Anything, 0, 10).Return(deployments, nil)
	repo.On("Count", mock.Anything).Return(int64(2), nil)

	router.GET("/deployments", handler.ListDeployments)

	req := httptest.NewRequest(http.MethodGet, "/deployments?offset=0&limit=10", nil)
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, float64(2), response["total"])

	repo.AssertExpectations(t)
}

func TestListDeployments_EmptyResult(t *testing.T) {
	router := setupTestRouter()
	handler, repo, _ := setupTestHandler()

	deployments := []*domain.Deployment{}
	repo.On("List", mock.Anything, 0, 10).Return(deployments, nil)
	repo.On("Count", mock.Anything).Return(int64(0), nil)

	router.GET("/deployments", handler.ListDeployments)

	req := httptest.NewRequest(http.MethodGet, "/deployments?offset=0&limit=10", nil)
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, float64(0), response["total"])

	repo.AssertExpectations(t)
}

func TestListDeployments_InvalidQuery(t *testing.T) {
	router := setupTestRouter()
	handler, _, _ := setupTestHandler()

	router.GET("/deployments", handler.ListDeployments)

	req := httptest.NewRequest(http.MethodGet, "/deployments?limit=invalid", nil)
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestListDeployments_RepositoryError(t *testing.T) {
	router := setupTestRouter()
	handler, repo, _ := setupTestHandler()

	repo.On("List", mock.Anything, 0, 10).Return(nil, errors.New("database error"))

	router.GET("/deployments", handler.ListDeployments)

	req := httptest.NewRequest(http.MethodGet, "/deployments?offset=0&limit=10", nil)
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusInternalServerError, w.Code)

	repo.AssertExpectations(t)
}

func TestListDeployments_Pagination(t *testing.T) {
	router := setupTestRouter()
	handler, repo, _ := setupTestHandler()

	dep1, _ := domain.NewDeployment("dep-1", "owner-1", nil)
	deployments := []*domain.Deployment{dep1}

	repo.On("List", mock.Anything, 20, 10).Return(deployments, nil)
	repo.On("Count", mock.Anything).Return(int64(25), nil)

	router.GET("/deployments", handler.ListDeployments)

	req := httptest.NewRequest(http.MethodGet, "/deployments?offset=20&limit=10", nil)
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, float64(20), response["offset"])
	assert.Equal(t, float64(10), response["limit"])

	repo.AssertExpectations(t)
}

func TestListDeployments_CountErrorGraceful(t *testing.T) {
	router := setupTestRouter()
	handler, repo, _ := setupTestHandler()

	dep1, _ := domain.NewDeployment("dep-1", "owner-1", nil)
	deployments := []*domain.Deployment{dep1}

	repo.On("List", mock.Anything, 0, 10).Return(deployments, nil)
	repo.On("Count", mock.Anything).Return(int64(0), errors.New("count error"))

	router.GET("/deployments", handler.ListDeployments)

	req := httptest.NewRequest(http.MethodGet, "/deployments?offset=0&limit=10", nil)
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	// Count errors are handled gracefully - should still return 200 with length-based total
	assert.Equal(t, http.StatusOK, w.Code)
	
	var response map[string]interface{}
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.Equal(t, float64(1), response["total"]) // Falls back to len(deployments)

	repo.AssertExpectations(t)
}
