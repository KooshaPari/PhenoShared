package handlers

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestNewDeploymentHandler(t *testing.T) {
	handler, _, _ := setupTestHandler()

	assert.NotNil(t, handler)
	assert.NotNil(t, handler.createUseCase)
	assert.NotNil(t, handler.getUseCase)
	assert.NotNil(t, handler.listUseCase)
	assert.NotNil(t, handler.terminateUseCase)
	assert.NotNil(t, handler.updateStatusUseCase)
}

func TestRegisterRoutes(t *testing.T) {
	router := setupTestRouter()
	handler, _, _ := setupTestHandler()
	
	v1 := router.Group("/api/v1")
	handler.RegisterRoutes(v1)

	routes := router.Routes()
	assert.True(t, len(routes) > 0)
}
