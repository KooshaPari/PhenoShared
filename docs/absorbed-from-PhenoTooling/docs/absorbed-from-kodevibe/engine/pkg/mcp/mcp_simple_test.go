package mcp

import (
	"context"
	"testing"
	"time"

	"kodevibe/internal/models"

	"github.com/stretchr/testify/assert"
)

func TestAnalysisContextCreation(t *testing.T) {
	scanResult := &models.ScanResult{
		ID:           "test-scan",
		ProjectPath:  "/test/project",
		FilesScanned: 10,
		Issues: []models.Issue{
			{
				File:     "test.go",
				Line:     10,
				Severity: models.SeverityWarning,
				Message:  "Test issue",
				Type:     models.VibeTypeSecurity,
			},
		},
		Summary: models.ScanSummary{
			Score: 85.5,
			Grade: "B",
		},
	}

	client := NewMCPClient("http://localhost:8080", "test-key")
	request := client.CreateAnalysisRequest(scanResult, "go")

	assert.NotNil(t, request)
	assert.Equal(t, "analyze_code_quality", request.Method)
	assert.NotNil(t, request.Context)
	assert.Equal(t, "go", request.Context.Language)
}

func TestMCPRequest_WithTimeout(t *testing.T) {
	client := NewMCPClient("http://localhost:8080", "test-key")

	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
	defer cancel()

	scanResult := &models.ScanResult{
		ID:     "test-scan",
		Issues: []models.Issue{},
		Summary: models.ScanSummary{
			Score: 75.0,
			Grade: "C",
		},
	}

	request := client.CreateAnalysisRequest(scanResult, "go")
	assert.NotNil(t, request)

	// Test context handling
	select {
	case <-ctx.Done():
		assert.Error(t, ctx.Err())
	default:
		// Context still valid
	}
}

func TestMCPContextMetadata(t *testing.T) {
	context := &MCPContext{
		ProjectPath: "/test/project",
		Language:    "go",
		Metadata: map[string]interface{}{
			"version":     "1.0.0",
			"framework":   "gin",
			"total_files": 25,
		},
		AIInstructions: "Focus on security improvements",
	}

	assert.Equal(t, "/test/project", context.ProjectPath)
	assert.Equal(t, "go", context.Language)
	assert.Equal(t, "1.0.0", context.Metadata["version"])
	assert.Equal(t, "gin", context.Metadata["framework"])
	assert.Equal(t, 25, context.Metadata["total_files"])
	assert.Contains(t, context.AIInstructions, "security")
}
