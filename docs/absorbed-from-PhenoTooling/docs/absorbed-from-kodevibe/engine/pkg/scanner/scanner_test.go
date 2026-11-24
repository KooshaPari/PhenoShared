package scanner

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"kodevibe/internal/models"
)

func TestNewScanner(t *testing.T) {
	config := &models.Configuration{
		Scanner: models.ScannerConfig{
			MaxConcurrency: 5,
			Timeout:        30,
			EnabledVibes:   []string{"security", "code"},
		},
	}
	logger := logrus.New()

	scanner, err := NewScanner(config, logger)

	assert.NoError(t, err)
	assert.NotNil(t, scanner)
	assert.Equal(t, 5, scanner.maxConcurrency)
	assert.Equal(t, 30*time.Second, scanner.timeout)
	assert.Len(t, scanner.vibes, 2)
}

func TestScanner_Scan(t *testing.T) {
	// Create temporary test files
	tempDir := t.TempDir()
	testFile := filepath.Join(tempDir, "test.js")

	testCode := `
function test() {
    var x = 1; // Should trigger var usage warning
    console.log("test"); // Should trigger console.log warning
    return x;
}
`

	err := os.WriteFile(testFile, []byte(testCode), 0644)
	require.NoError(t, err)

	config := &models.Configuration{
		Scanner: models.ScannerConfig{
			MaxConcurrency: 2,
			Timeout:        10,
			EnabledVibes:   []string{"code"},
		},
	}
	logger := logrus.New()
	logger.SetLevel(logrus.WarnLevel) // Reduce test output

	scanner, err := NewScanner(config, logger)
	require.NoError(t, err)

	request := &models.ScanRequest{
		ID:    "test-scan-1",
		Paths: []string{tempDir},
		Vibes: []string{"code"},
	}

	ctx := context.Background()
	result, err := scanner.Scan(ctx, request)

	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "test-scan-1", result.ScanID)
	assert.Greater(t, len(result.Issues), 0)

	// Check for expected issues
	hasConsoleLogIssue := false
	hasVarIssue := false

	for _, issue := range result.Issues {
		if issue.Rule == "no-console-log" {
			hasConsoleLogIssue = true
		}
		if issue.Rule == "no-var" {
			hasVarIssue = true
		}
	}

	assert.True(t, hasConsoleLogIssue, "Should detect console.log usage")
	assert.True(t, hasVarIssue, "Should detect var usage")
}

func TestScanner_ScanWithInvalidPaths(t *testing.T) {
	config := &models.Configuration{
		Scanner: models.ScannerConfig{
			MaxConcurrency: 2,
			Timeout:        10,
			EnabledVibes:   []string{"code"},
		},
	}
	logger := logrus.New()
	logger.SetLevel(logrus.WarnLevel)

	scanner, err := NewScanner(config, logger)
	require.NoError(t, err)

	request := &models.ScanRequest{
		ID:    "test-scan-2",
		Paths: []string{"/nonexistent/path"},
		Vibes: []string{"code"},
	}

	ctx := context.Background()
	result, err := scanner.Scan(ctx, request)

	assert.NoError(t, err) // Scanner should handle invalid paths gracefully
	assert.NotNil(t, result)
	assert.Equal(t, "test-scan-2", result.ScanID)
	assert.Equal(t, 0, len(result.Issues)) // No issues from nonexistent paths
}

func TestScanner_ScanWithContext(t *testing.T) {
	tempDir := t.TempDir()

	// Create multiple test files
	for i := 0; i < 5; i++ {
		testFile := filepath.Join(tempDir, fmt.Sprintf("test%d.js", i))
		testCode := `console.log("test");`
		err := os.WriteFile(testFile, []byte(testCode), 0644)
		require.NoError(t, err)
	}

	config := &models.Configuration{
		Scanner: models.ScannerConfig{
			MaxConcurrency: 1, // Low concurrency to make test more predictable
			Timeout:        10,
			EnabledVibes:   []string{"code"},
		},
	}
	logger := logrus.New()
	logger.SetLevel(logrus.WarnLevel)

	scanner, err := NewScanner(config, logger)
	require.NoError(t, err)

	request := &models.ScanRequest{
		ID:    "test-scan-3",
		Paths: []string{tempDir},
		Vibes: []string{"code"},
	}

	// Test context cancellation
	ctx, cancel := context.WithTimeout(context.Background(), 1*time.Millisecond)
	defer cancel()

	result, err := scanner.Scan(ctx, request)

	// Should handle context cancellation gracefully
	if err != nil {
		assert.Contains(t, err.Error(), "context")
	} else {
		// Or complete successfully if fast enough
		assert.NotNil(t, result)
	}
}

func TestScanner_discoverFiles(t *testing.T) {
	tempDir := t.TempDir()

	// Create test file structure
	subDir := filepath.Join(tempDir, "subdir")
	err := os.Mkdir(subDir, 0755)
	require.NoError(t, err)

	files := []string{
		filepath.Join(tempDir, "test.js"),
		filepath.Join(tempDir, "test.go"),
		filepath.Join(subDir, "nested.py"),
		filepath.Join(tempDir, "ignore.txt"),
	}

	for _, file := range files {
		err := os.WriteFile(file, []byte("test content"), 0644)
		require.NoError(t, err)
	}

	config := &models.Configuration{
		Scanner: models.ScannerConfig{
			ExcludePatterns: []string{"*.txt"},
		},
	}
	logger := logrus.New()

	scanner, err := NewScanner(config, logger)
	require.NoError(t, err)

	discoveredFiles, err := scanner.discoverFiles([]string{tempDir}, false, "")

	assert.NoError(t, err)
	assert.Contains(t, discoveredFiles, filepath.Join(tempDir, "test.js"))
	assert.Contains(t, discoveredFiles, filepath.Join(tempDir, "test.go"))
	assert.Contains(t, discoveredFiles, filepath.Join(subDir, "nested.py"))
	assert.NotContains(t, discoveredFiles, filepath.Join(tempDir, "ignore.txt"))
}

func TestScanner_shouldIgnore(t *testing.T) {
	config := &models.Configuration{
		Scanner: models.ScannerConfig{
			ExcludePatterns: []string{
				"*.tmp",
				"node_modules/*",
				".git/*",
			},
		},
	}
	logger := logrus.New()

	scanner, err := NewScanner(config, logger)
	require.NoError(t, err)

	tests := []struct {
		path     string
		expected bool
	}{
		{"test.js", false},
		{"test.tmp", true},
		{"node_modules/package/index.js", true},
		{".git/config", true},
		{"src/main.go", false},
	}

	for _, test := range tests {
		result := scanner.shouldIgnore(test.path)
		assert.Equal(t, test.expected, result, "Path: %s", test.path)
	}
}

// Benchmark tests
func BenchmarkScanner_Scan(b *testing.B) {
	tempDir := b.TempDir()

	// Create multiple test files
	for i := 0; i < 10; i++ {
		testFile := filepath.Join(tempDir, fmt.Sprintf("test%d.js", i))
		testCode := `
function test() {
    var x = 1;
    console.log("test");
    return x;
}
`
		err := os.WriteFile(testFile, []byte(testCode), 0644)
		require.NoError(b, err)
	}

	config := &models.Configuration{
		Scanner: models.ScannerConfig{
			MaxConcurrency: 4,
			Timeout:        30,
			EnabledVibes:   []string{"code"},
		},
	}
	logger := logrus.New()
	logger.SetLevel(logrus.WarnLevel)

	scanner, err := NewScanner(config, logger)
	require.NoError(b, err)

	request := &models.ScanRequest{
		ID:    "bench-scan",
		Paths: []string{tempDir},
		Vibes: []string{"code"},
	}

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		ctx := context.Background()
		_, err := scanner.Scan(ctx, request)
		require.NoError(b, err)
	}
}
