package mcp

import (
	"context"
	"testing"
	"time"

	"kodevibe/internal/models"

	"github.com/stretchr/testify/assert"
)

func TestNewMCPClient(t *testing.T) {
	client := NewMCPClient("http://localhost:8080", "test-api-key")

	assert.NotNil(t, client)
	assert.Equal(t, "http://localhost:8080", client.baseURL)
	assert.Equal(t, "test-api-key", client.apiKey)
	assert.Equal(t, 30*time.Second, client.timeout)
}

func TestAnalyzeCodeQuality(t *testing.T) {
	client := NewMCPClient("http://localhost:8080", "test-key")

	scanResult := &models.ScanResult{
		ID:        "test-scan",
		Timestamp: time.Now(),
		Issues: []models.Issue{
			{
				Type:     models.VibeTypeSecurity,
				Severity: models.SeverityError,
				Title:    "Test security issue",
				File:     "test.go",
				Line:     10,
			},
		},
		Summary: models.ScanSummary{
			TotalIssues:   1,
			ErrorCount:    1,
			WarningCount:  0,
			InfoCount:     0,
			CriticalCount: 0,
			Score:         75.5,
			Grade:         "B",
		},
	}

	targets := GetQualityTargets(75.5, "B")

	ctx := context.Background()
	response, err := client.AnalyzeCodeQuality(ctx, scanResult, targets)

	assert.NoError(t, err)
	assert.NotNil(t, response)
	assert.NotEmpty(t, response.ID)
	assert.NotNil(t, response.Result)

	// Check if analysis results are present
	if analysis, ok := response.Result["analysis"]; ok {
		analysisMap := analysis.(map[string]interface{})
		assert.Contains(t, analysisMap, "overall_score")
		assert.Contains(t, analysisMap, "grade")
		assert.Contains(t, analysisMap, "improvements")
	}
}

func TestSuggestImprovements(t *testing.T) {
	client := NewMCPClient("http://localhost:8080", "test-key")

	issues := []models.Issue{
		{
			Type:     models.VibeTypeCode,
			Severity: models.SeverityWarning,
			Title:    "Function too complex",
			File:     "complex.go",
			Line:     25,
			Rule:     "cyclomatic-complexity",
		},
	}

	mcpContext := &MCPContext{
		ProjectPath: "/test/project",
		Language:    "go",
		Issues:      issues,
	}

	ctx := context.Background()
	optimizations, err := client.SuggestImprovements(ctx, issues, mcpContext)

	assert.NoError(t, err)
	assert.NotNil(t, optimizations)
}

func TestGenerateFixStrategies(t *testing.T) {
	client := NewMCPClient("http://localhost:8080", "test-key")

	issues := []models.Issue{
		{
			Type:     models.VibeTypeSecurity,
			Severity: models.SeverityError,
			Title:    "Hardcoded secret",
			File:     "config.go",
			Line:     15,
			Rule:     "hardcoded-secrets",
		},
	}

	projectContext := &MCPContext{
		ProjectPath: "/test/project",
		Language:    "go",
		Issues:      issues,
	}

	ctx := context.Background()
	strategies, err := client.GenerateFixStrategies(ctx, issues, projectContext)

	assert.NoError(t, err)
	assert.NotNil(t, strategies)
}

func TestValidateAIFixes(t *testing.T) {
	client := NewMCPClient("http://localhost:8080", "test-key")

	changes := []FileChange{
		{
			FilePath:      "test.go",
			LineStart:     10,
			LineEnd:       15,
			OriginalCode:  "original code",
			SuggestedCode: "improved code",
			Reasoning:     "Better security practices",
		},
	}

	mcpContext := &MCPContext{
		ProjectPath: "/test/project",
		Language:    "go",
	}

	ctx := context.Background()
	validation, err := client.ValidateAIFixes(ctx, changes, mcpContext)

	assert.NoError(t, err)
	assert.NotNil(t, validation)
	assert.True(t, validation.IsValid)
	assert.Greater(t, validation.SafetyScore, 0.0)
}

func TestCreateProjectContext(t *testing.T) {
	scanResult := &models.ScanResult{
		ID:        "test-scan",
		Timestamp: time.Now(),
		Duration:  2 * time.Second,
		Files:     []string{"file1.go", "file2.go"},
		Issues: []models.Issue{
			{
				Type:     models.VibeTypeCode,
				Severity: models.SeverityInfo,
				Title:    "Test issue",
			},
		},
		Summary: models.ScanSummary{
			Grade: "B",
		},
	}

	mcpContext := CreateProjectContext(scanResult, "/test/project", "go")

	assert.NotNil(t, mcpContext)
	assert.Equal(t, "/test/project", mcpContext.ProjectPath)
	assert.Equal(t, "go", mcpContext.Language)
	assert.Equal(t, scanResult, mcpContext.ScanResults)
	assert.Equal(t, scanResult.Issues, mcpContext.Issues)
	assert.NotNil(t, mcpContext.Metadata)
	assert.Contains(t, mcpContext.AIInstructions, "go project")
}

func TestGetQualityTargets(t *testing.T) {
	targets := GetQualityTargets(75.5, "B")

	assert.NotNil(t, targets)
	assert.Equal(t, 85.5, targets.MinScore)
	assert.Equal(t, 5, targets.MaxIssues)
	assert.Equal(t, "A", targets.RequiredGrade)
	assert.Contains(t, targets.FocusAreas, "security")
	assert.Contains(t, targets.FocusAreas, "performance")
	assert.Contains(t, targets.FocusAreas, "maintainability")
}

func TestGetNextGrade(t *testing.T) {
	tests := []struct {
		current  string
		expected string
	}{
		{"F", "D"},
		{"D", "C"},
		{"C", "B"},
		{"B", "A"},
		{"A", "A+"},
		{"A+", "A+"},
		{"Unknown", "A"},
	}

	for _, test := range tests {
		result := getNextGrade(test.current)
		assert.Equal(t, test.expected, result, "Grade progression for %s", test.current)
	}
}

func TestMCPRequest(t *testing.T) {
	request := &MCPRequest{
		ID:          "test-123",
		Method:      "test_method",
		RequestType: "test",
		Timestamp:   time.Now(),
		Params: map[string]interface{}{
			"param1": "value1",
			"param2": 42,
		},
	}

	assert.Equal(t, "test-123", request.ID)
	assert.Equal(t, "test_method", request.Method)
	assert.Equal(t, "test", request.RequestType)
	assert.NotNil(t, request.Params)
	assert.Equal(t, "value1", request.Params["param1"])
	assert.Equal(t, 42, request.Params["param2"])
}

func TestAIOptimization(t *testing.T) {
	optimization := AIOptimization{
		Type:        "security",
		Description: "Fix hardcoded secret",
		Impact:      "high",
		Confidence:  0.95,
		Suggestion:  "Use environment variables",
		FileChanges: []FileChange{
			{
				FilePath:      "config.go",
				LineStart:     10,
				LineEnd:       10,
				OriginalCode:  `secret := "hardcoded"`,
				SuggestedCode: `secret := os.Getenv("SECRET")`,
				Reasoning:     "Environment variables are more secure",
			},
		},
	}

	assert.Equal(t, "security", optimization.Type)
	assert.Equal(t, "high", optimization.Impact)
	assert.Equal(t, 0.95, optimization.Confidence)
	assert.Len(t, optimization.FileChanges, 1)
	assert.Equal(t, "config.go", optimization.FileChanges[0].FilePath)
}

// Benchmark tests for performance
func BenchmarkAnalyzeCodeQuality(b *testing.B) {
	client := NewMCPClient("http://localhost:8080", "test-key")

	scanResult := &models.ScanResult{
		ID:        "bench-scan",
		Timestamp: time.Now(),
		Issues:    []models.Issue{},
		Summary: models.ScanSummary{
			Score: 80.0,
			Grade: "B",
		},
	}

	targets := GetQualityTargets(80.0, "B")
	ctx := context.Background()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := client.AnalyzeCodeQuality(ctx, scanResult, targets)
		if err != nil {
			b.Fatal(err)
		}
	}
}

func BenchmarkCreateProjectContext(b *testing.B) {
	scanResult := &models.ScanResult{
		ID:        "bench-scan",
		Timestamp: time.Now(),
		Duration:  time.Second,
		Files:     []string{"file1.go", "file2.go", "file3.go"},
		Issues:    make([]models.Issue, 10),
		Summary: models.ScanSummary{
			Grade: "B",
		},
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		mcpContext := CreateProjectContext(scanResult, "/test/project", "go")
		if mcpContext == nil {
			b.Fatal("Context creation failed")
		}
	}
}
