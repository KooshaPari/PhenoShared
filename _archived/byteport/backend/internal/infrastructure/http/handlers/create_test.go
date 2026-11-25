package handlers

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/byteport/api/internal/application/deployment"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

func TestCreateDeployment_Success(t *testing.T) {
	router := setupTestRouter()
	handler, repo, svc := setupTestHandler()

	svc.On("ValidateDeployment", mock.Anything, mock.Anything).Return(nil)
	repo.On("Create", mock.Anything, mock.Anything).Return(nil)

	router.POST("/deployments", handler.CreateDeployment)

	reqBody := deployment.CreateDeploymentRequest{
		Name:    "test-deployment",
		Owner:   "test-owner",
		EnvVars: map[string]string{"KEY": "value"},
	}
	body, _ := json.Marshal(reqBody)

	req := httptest.NewRequest(http.MethodPost, "/deployments", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusCreated, w.Code)
	
	var response deployment.CreateDeploymentResponse
	err := json.Unmarshal(w.Body.Bytes(), &response)
	assert.NoError(t, err)
	assert.NotEmpty(t, response.UUID)

	repo.AssertExpectations(t)
	svc.AssertExpectations(t)
}

func TestCreateDeployment_InvalidJSON(t *testing.T) {
	router := setupTestRouter()
	handler, _, _ := setupTestHandler()

	router.POST("/deployments", handler.CreateDeployment)

	req := httptest.NewRequest(http.MethodPost, "/deployments", bytes.NewReader([]byte("invalid json")))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusBadRequest, w.Code)
}

func TestCreateDeployment_RepositoryError(t *testing.T) {
	router := setupTestRouter()
	handler, repo, svc := setupTestHandler()

	svc.On("ValidateDeployment", mock.Anything, mock.Anything).Return(nil)
	repo.On("Create", mock.Anything, mock.Anything).Return(errors.New("database error"))

	router.POST("/deployments", handler.CreateDeployment)

	reqBody := deployment.CreateDeploymentRequest{
		Name:  "test",
		Owner: "owner",
	}
	body, _ := json.Marshal(reqBody)

	req := httptest.NewRequest(http.MethodPost, "/deployments", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusInternalServerError, w.Code)

	repo.AssertExpectations(t)
}
