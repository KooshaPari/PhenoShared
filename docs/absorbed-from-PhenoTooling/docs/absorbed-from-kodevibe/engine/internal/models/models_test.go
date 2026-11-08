package models

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestSeverityLevel_String(t *testing.T) {
	tests := []struct {
		severity SeverityLevel
		expected string
	}{
		{SeverityInfo, "info"},
		{SeverityWarning, "warning"},
		{SeverityError, "error"},
		{SeverityCritical, "critical"},
	}

	for _, test := range tests {
		assert.Equal(t, test.expected, string(test.severity))
	}
}

func TestVibeType_String(t *testing.T) {
	tests := []struct {
		vibeType VibeType
		expected string
	}{
		{VibeTypeSecurity, "security"},
		{VibeTypeCode, "code"},
		{VibeTypePerformance, "performance"},
		{VibeTypeFile, "file"},
		{VibeTypeGit, "git"},
		{VibeTypeDependency, "dependency"},
		{VibeTypeDocumentation, "documentation"},
	}

	for _, test := range tests {
		assert.Equal(t, test.expected, string(test.vibeType))
	}
}

func TestReportFormat_String(t *testing.T) {
	tests := []struct {
		format   ReportFormat
		expected string
	}{
		{ReportFormatText, "text"},
		{ReportFormatJSON, "json"},
		{ReportFormatHTML, "html"},
		{ReportFormatXML, "xml"},
		{ReportFormatJUnit, "junit"},
		{ReportFormatCSV, "csv"},
	}

	for _, test := range tests {
		assert.Equal(t, test.expected, string(test.format))
	}
}

func TestIssue_Validate(t *testing.T) {
	// Valid issue
	validIssue := Issue{
		Type:       VibeTypeSecurity,
		Severity:   SeverityError,
		Title:      "Test Issue",
		Message:    "This is a test issue",
		File:       "test.js",
		Line:       10,
		Rule:       "test-rule",
		Confidence: 0.9,
	}

	assert.True(t, validIssue.IsValid())

	// Invalid issue - missing title
	invalidIssue := validIssue
	invalidIssue.Title = ""
	assert.False(t, invalidIssue.IsValid())

	// Invalid issue - missing message
	invalidIssue = validIssue
	invalidIssue.Message = ""
	assert.False(t, invalidIssue.IsValid())

	// Invalid issue - missing file
	invalidIssue = validIssue
	invalidIssue.File = ""
	assert.False(t, invalidIssue.IsValid())

	// Invalid issue - negative line
	invalidIssue = validIssue
	invalidIssue.Line = -1
	assert.False(t, invalidIssue.IsValid())

	// Invalid issue - confidence out of range
	invalidIssue = validIssue
	invalidIssue.Confidence = 1.5
	assert.False(t, invalidIssue.IsValid())
}

func TestIssue_IsValid(t *testing.T) {
	tests := []struct {
		name     string
		issue    Issue
		expected bool
	}{
		{
			name: "valid issue",
			issue: Issue{
				Type:       VibeTypeCode,
				Severity:   SeverityWarning,
				Title:      "Line too long",
				Message:    "Line exceeds maximum length",
				File:       "test.js",
				Line:       5,
				Rule:       "line-length",
				Confidence: 1.0,
			},
			expected: true,
		},
		{
			name: "missing title",
			issue: Issue{
				Type:     VibeTypeCode,
				Severity: SeverityWarning,
				Message:  "Line exceeds maximum length",
				File:     "test.js",
				Line:     5,
			},
			expected: false,
		},
		{
			name: "zero line number",
			issue: Issue{
				Type:     VibeTypeCode,
				Severity: SeverityWarning,
				Title:    "Test",
				Message:  "Test message",
				File:     "test.js",
				Line:     0,
			},
			expected: false,
		},
		{
			name: "confidence too high",
			issue: Issue{
				Type:       VibeTypeCode,
				Severity:   SeverityWarning,
				Title:      "Test",
				Message:    "Test message",
				File:       "test.js",
				Line:       1,
				Confidence: 2.0,
			},
			expected: false,
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			assert.Equal(t, test.expected, test.issue.IsValid())
		})
	}
}

func TestScanRequest_Validate(t *testing.T) {
	// Valid request
	validRequest := ScanRequest{
		ID:        "test-scan",
		Paths:     []string{"/tmp/test"},
		Vibes:     []string{"security", "code"},
		Format:    ReportFormatJSON,
		CreatedAt: time.Now(),
	}

	assert.True(t, validRequest.IsValid())

	// Invalid request - no paths
	invalidRequest := validRequest
	invalidRequest.Paths = []string{}
	assert.False(t, invalidRequest.IsValid())

	// Invalid request - empty path
	invalidRequest = validRequest
	invalidRequest.Paths = []string{""}
	assert.False(t, invalidRequest.IsValid())

	// Invalid request - no vibes
	invalidRequest = validRequest
	invalidRequest.Vibes = []string{}
	assert.False(t, invalidRequest.IsValid())

	// Invalid request - empty vibe
	invalidRequest = validRequest
	invalidRequest.Vibes = []string{""}
	assert.False(t, invalidRequest.IsValid())
}

func TestScanRequest_IsValid(t *testing.T) {
	tests := []struct {
		name     string
		request  ScanRequest
		expected bool
	}{
		{
			name: "valid request",
			request: ScanRequest{
				ID:     "test",
				Paths:  []string{"/tmp"},
				Vibes:  []string{"code"},
				Format: ReportFormatJSON,
			},
			expected: true,
		},
		{
			name: "empty paths",
			request: ScanRequest{
				ID:     "test",
				Paths:  []string{},
				Vibes:  []string{"code"},
				Format: ReportFormatJSON,
			},
			expected: false,
		},
		{
			name: "empty vibes",
			request: ScanRequest{
				ID:     "test",
				Paths:  []string{"/tmp"},
				Vibes:  []string{},
				Format: ReportFormatJSON,
			},
			expected: false,
		},
		{
			name: "empty path in slice",
			request: ScanRequest{
				ID:     "test",
				Paths:  []string{"/tmp", ""},
				Vibes:  []string{"code"},
				Format: ReportFormatJSON,
			},
			expected: false,
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			assert.Equal(t, test.expected, test.request.IsValid())
		})
	}
}

func TestScanResult_CalculateSummary(t *testing.T) {
	issues := []Issue{
		{
			Type:     VibeTypeSecurity,
			Severity: SeverityError,
			File:     "file1.js",
		},
		{
			Type:     VibeTypeSecurity,
			Severity: SeverityCritical,
			File:     "file1.js",
		},
		{
			Type:     VibeTypeCode,
			Severity: SeverityWarning,
			File:     "file2.js",
		},
		{
			Type:     VibeTypeCode,
			Severity: SeverityInfo,
			File:     "file2.js",
		},
	}

	result := ScanResult{
		Issues: issues,
	}

	summary := result.CalculateSummary()

	assert.Equal(t, 4, summary.TotalIssues)
	assert.Equal(t, 1, summary.CriticalIssues)
	assert.Equal(t, 1, summary.ErrorIssues)
	assert.Equal(t, 1, summary.WarningIssues)
	assert.Equal(t, 1, summary.InfoIssues)
	assert.Equal(t, 2, summary.FilesScanned)

	// Test issue breakdown by type
	assert.Equal(t, 2, summary.IssuesByType[VibeTypeSecurity])
	assert.Equal(t, 2, summary.IssuesByType[VibeTypeCode])
}

func TestScanResult_GetIssuesBySeverity(t *testing.T) {
	issues := []Issue{
		{Severity: SeverityError, Title: "Error 1"},
		{Severity: SeverityWarning, Title: "Warning 1"},
		{Severity: SeverityError, Title: "Error 2"},
		{Severity: SeverityInfo, Title: "Info 1"},
	}

	result := ScanResult{Issues: issues}

	errorIssues := result.GetIssuesBySeverity(SeverityError)
	assert.Len(t, errorIssues, 2)
	assert.Equal(t, "Error 1", errorIssues[0].Title)
	assert.Equal(t, "Error 2", errorIssues[1].Title)

	warningIssues := result.GetIssuesBySeverity(SeverityWarning)
	assert.Len(t, warningIssues, 1)
	assert.Equal(t, "Warning 1", warningIssues[0].Title)

	criticalIssues := result.GetIssuesBySeverity(SeverityCritical)
	assert.Len(t, criticalIssues, 0)
}

func TestScanResult_GetIssuesByType(t *testing.T) {
	issues := []Issue{
		{Type: VibeTypeSecurity, Title: "Security 1"},
		{Type: VibeTypeCode, Title: "Code 1"},
		{Type: VibeTypeSecurity, Title: "Security 2"},
		{Type: VibeTypePerformance, Title: "Performance 1"},
	}

	result := ScanResult{Issues: issues}

	securityIssues := result.GetIssuesByType(VibeTypeSecurity)
	assert.Len(t, securityIssues, 2)
	assert.Equal(t, "Security 1", securityIssues[0].Title)
	assert.Equal(t, "Security 2", securityIssues[1].Title)

	codeIssues := result.GetIssuesByType(VibeTypeCode)
	assert.Len(t, codeIssues, 1)
	assert.Equal(t, "Code 1", codeIssues[0].Title)

	fileIssues := result.GetIssuesByType(VibeTypeFile)
	assert.Len(t, fileIssues, 0)
}

func TestScanResult_GetIssuesByFile(t *testing.T) {
	issues := []Issue{
		{File: "file1.js", Title: "Issue 1"},
		{File: "file2.js", Title: "Issue 2"},
		{File: "file1.js", Title: "Issue 3"},
	}

	result := ScanResult{Issues: issues}

	file1Issues := result.GetIssuesByFile("file1.js")
	assert.Len(t, file1Issues, 2)
	assert.Equal(t, "Issue 1", file1Issues[0].Title)
	assert.Equal(t, "Issue 3", file1Issues[1].Title)

	file2Issues := result.GetIssuesByFile("file2.js")
	assert.Len(t, file2Issues, 1)
	assert.Equal(t, "Issue 2", file2Issues[0].Title)

	file3Issues := result.GetIssuesByFile("file3.js")
	assert.Len(t, file3Issues, 0)
}

func TestConfiguration_Validate(t *testing.T) {
	// Valid configuration
	validConfig := Configuration{
		Scanner: ScannerConfig{
			MaxConcurrency: 4,
			Timeout:        30,
			EnabledVibes:   []string{"security", "code"},
		},
		Server: ServerConfig{
			Host: "localhost",
			Port: 8080,
		},
	}

	assert.True(t, validConfig.IsValid())

	// Invalid configuration - invalid concurrency
	invalidConfig := validConfig
	invalidConfig.Scanner.MaxConcurrency = 0
	assert.False(t, invalidConfig.IsValid())

	// Invalid configuration - invalid timeout
	invalidConfig = validConfig
	invalidConfig.Scanner.Timeout = -1
	assert.False(t, invalidConfig.IsValid())

	// Invalid configuration - invalid port
	invalidConfig = validConfig
	invalidConfig.Server.Port = 0
	assert.False(t, invalidConfig.IsValid())
}

func TestConfiguration_IsValid(t *testing.T) {
	tests := []struct {
		name     string
		config   Configuration
		expected bool
	}{
		{
			name: "valid config",
			config: Configuration{
				Scanner: ScannerConfig{
					MaxConcurrency: 4,
					Timeout:        30,
					EnabledVibes:   []string{"security"},
				},
				Server: ServerConfig{
					Host: "localhost",
					Port: 8080,
				},
			},
			expected: true,
		},
		{
			name: "zero concurrency",
			config: Configuration{
				Scanner: ScannerConfig{
					MaxConcurrency: 0,
					Timeout:        30,
				},
			},
			expected: false,
		},
		{
			name: "negative timeout",
			config: Configuration{
				Scanner: ScannerConfig{
					MaxConcurrency: 4,
					Timeout:        -1,
				},
			},
			expected: false,
		},
		{
			name: "invalid port",
			config: Configuration{
				Scanner: ScannerConfig{
					MaxConcurrency: 4,
					Timeout:        30,
				},
				Server: ServerConfig{
					Port: 70000,
				},
			},
			expected: false,
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			assert.Equal(t, test.expected, test.config.IsValid())
		})
	}
}

func TestVibeConfig_IsEnabled(t *testing.T) {
	enabled := VibeConfig{Enabled: true}
	disabled := VibeConfig{Enabled: false}

	assert.True(t, enabled.IsEnabled())
	assert.False(t, disabled.IsEnabled())
}

// Benchmark tests
func BenchmarkScanResult_CalculateSummary(b *testing.B) {
	// Create a large set of issues
	issues := make([]Issue, 1000)
	for i := 0; i < 1000; i++ {
		issues[i] = Issue{
			Type:     VibeTypeSecurity,
			Severity: SeverityWarning,
			File:     "test.js",
		}
	}

	result := ScanResult{Issues: issues}

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		result.CalculateSummary()
	}
}

func BenchmarkScanResult_GetIssuesBySeverity(b *testing.B) {
	// Create a large set of issues
	issues := make([]Issue, 1000)
	for i := 0; i < 1000; i++ {
		if i%2 == 0 {
			issues[i] = Issue{Severity: SeverityError}
		} else {
			issues[i] = Issue{Severity: SeverityWarning}
		}
	}

	result := ScanResult{Issues: issues}

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		result.GetIssuesBySeverity(SeverityError)
	}
}
