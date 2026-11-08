package mcp

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestMCPRequest_Creation(t *testing.T) {
	request := &MCPRequest{
		ID:        "test-123",
		Method:    "analyze_code",
		Params:    map[string]interface{}{"code": "test code"},
		Timestamp: time.Now(),
	}

	assert.NotNil(t, request)
	assert.Equal(t, "test-123", request.ID)
	assert.Equal(t, "analyze_code", request.Method)
	assert.NotNil(t, request.Params)
}

func TestMCPResponse_Creation(t *testing.T) {
	response := &MCPResponse{
		ID:     "test-123",
		Result: map[string]interface{}{"score": 85.5},
	}

	assert.NotNil(t, response)
	assert.Equal(t, "test-123", response.ID)
	assert.NotNil(t, response.Result)
	assert.Nil(t, response.Error)
}

func TestMCPResponse_WithError(t *testing.T) {
	response := &MCPResponse{
		ID: "test-456",
		Error: &MCPError{
			Code:    404,
			Message: "Method not found",
		},
	}

	assert.NotNil(t, response)
	assert.Equal(t, "test-456", response.ID)
	assert.Nil(t, response.Result)
	assert.NotNil(t, response.Error)
	assert.Equal(t, 404, response.Error.Code)
	assert.Equal(t, "Method not found", response.Error.Message)
}

func TestMCPContext_Creation(t *testing.T) {
	context := &MCPContext{
		ProjectPath: "/test/project",
		Language:    "go",
		Metadata:    map[string]interface{}{"version": "1.0"},
	}

	assert.NotNil(t, context)
	assert.Equal(t, "/test/project", context.ProjectPath)
	assert.Equal(t, "go", context.Language)
	assert.NotNil(t, context.Metadata)
}

func TestMCPClient_BasicCreation(t *testing.T) {
	client := NewMCPClient("http://localhost:8080", "test-key")

	assert.NotNil(t, client)
	assert.Equal(t, "http://localhost:8080", client.baseURL)
	assert.Equal(t, "test-key", client.apiKey)
	assert.NotNil(t, client.logger)
	assert.NotNil(t, client.httpClient)
}
