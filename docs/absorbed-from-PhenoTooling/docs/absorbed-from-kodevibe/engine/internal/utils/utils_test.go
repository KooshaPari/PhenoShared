package utils

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestTruncateString(t *testing.T) {
	tests := []struct {
		input    string
		maxLen   int
		expected string
	}{
		{"short", 10, "short"},
		{"this is a long string", 10, "this is a "},
		{"exactly ten", 10, "exactly te"},
		{"", 5, ""},
		{"abc", 0, ""},
	}

	for _, test := range tests {
		result := TruncateString(test.input, test.maxLen)
		assert.Equal(t, test.expected, result, "Input: %s, MaxLen: %d", test.input, test.maxLen)
	}
}

func TestContainsString(t *testing.T) {
	slice := []string{"apple", "banana", "cherry"}

	tests := []struct {
		item     string
		expected bool
	}{
		{"apple", true},
		{"banana", true},
		{"grape", false},
		{"", false},
	}

	for _, test := range tests {
		result := ContainsString(slice, test.item)
		assert.Equal(t, test.expected, result, "Item: %s", test.item)
	}
}

func TestUniqueStrings(t *testing.T) {
	tests := []struct {
		input    []string
		expected []string
	}{
		{
			[]string{"a", "b", "c"},
			[]string{"a", "b", "c"},
		},
		{
			[]string{"a", "b", "a", "c", "b"},
			[]string{"a", "b", "c"},
		},
		{
			[]string{},
			[]string{},
		},
		{
			[]string{"same", "same", "same"},
			[]string{"same"},
		},
	}

	for _, test := range tests {
		result := UniqueStrings(test.input)
		assert.ElementsMatch(t, test.expected, result)
	}
}

func TestEnsureDir(t *testing.T) {
	// Test with temporary directory
	tempDir := t.TempDir()
	testPath := tempDir + "/test/nested/dir"

	err := EnsureDir(testPath)
	assert.NoError(t, err)

	// Check that directory was created
	assert.DirExists(t, testPath)
}

func TestFileExists(t *testing.T) {
	// Test with temporary file
	tempDir := t.TempDir()
	existingFile := tempDir + "/existing.txt"

	// Create a test file
	err := createTestFile(existingFile, "test content")
	assert.NoError(t, err)

	tests := []struct {
		path     string
		expected bool
	}{
		{existingFile, true},
		{tempDir + "/nonexistent.txt", false},
		{tempDir, false}, // Directory, not file
	}

	for _, test := range tests {
		result := FileExists(test.path)
		assert.Equal(t, test.expected, result, "Path: %s", test.path)
	}
}

func TestIsGitRepo(t *testing.T) {
	tempDir := t.TempDir()

	// Test non-git directory
	assert.False(t, IsGitRepo(tempDir))

	// Create .git directory
	gitDir := tempDir + "/.git"
	err := EnsureDir(gitDir)
	assert.NoError(t, err)

	// Test git directory
	assert.True(t, IsGitRepo(tempDir))
}

func TestGetRelativePath(t *testing.T) {
	if os.PathSeparator == '\\' {
		t.Skip("POSIX path fixtures; CI runs on Linux")
	}
	tests := []struct {
		base     string
		target   string
		expected string
	}{
		{"/home/user", "/home/user/project/file.go", "project/file.go"},
		{"/home/user/", "/home/user/project/file.go", "project/file.go"},
		{"/home/user", "/home/user", "."},
		{"/different/path", "/home/user/file.go", "/home/user/file.go"},
	}

	for _, test := range tests {
		result := GetRelativePath(test.base, test.target)
		assert.Equal(t, test.expected, result, "Base: %s, Target: %s", test.base, test.target)
	}
}

func TestSanitizeFileName(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"normal_file.txt", "normal_file.txt"},
		{"file with spaces.txt", "file_with_spaces.txt"},
		{"file/with\\slashes.txt", "file_with_slashes.txt"},
		{"file:with*special<chars>.txt", "file_with_special_chars_.txt"},
		{"file\"with'quotes.txt", "file_with_quotes.txt"},
	}

	for _, test := range tests {
		result := SanitizeFileName(test.input)
		assert.Equal(t, test.expected, result, "Input: %s", test.input)
	}
}

func TestHash(t *testing.T) {
	tests := []struct {
		input string
	}{
		{"test string"},
		{"another test"},
		{""},
		{"special chars: !@#$%^&*()"},
	}

	for _, test := range tests {
		result := Hash(test.input)

		// Hash should be 64 characters (SHA256 hex)
		assert.Len(t, result, 64)

		// Same input should produce same hash
		assert.Equal(t, result, Hash(test.input))
	}

	// Different inputs should produce different hashes
	hash1 := Hash("test1")
	hash2 := Hash("test2")
	assert.NotEqual(t, hash1, hash2)
}

func TestFormatBytes(t *testing.T) {
	tests := []struct {
		bytes    int64
		expected string
	}{
		{0, "0 B"},
		{512, "512 B"},
		{1024, "1.0 KB"},
		{1536, "1.5 KB"},
		{1024 * 1024, "1.0 MB"},
		{1024 * 1024 * 1024, "1.0 GB"},
		{1024 * 1024 * 1024 * 1024, "1.0 TB"},
	}

	for _, test := range tests {
		result := FormatBytes(test.bytes)
		assert.Equal(t, test.expected, result, "Bytes: %d", test.bytes)
	}
}

func TestFormatDuration(t *testing.T) {
	tests := []struct {
		ms       int64
		expected string
	}{
		{0, "0ms"},
		{500, "500ms"},
		{1000, "1.0s"},
		{1500, "1.5s"},
		{60000, "1m0s"},
		{90000, "1m30s"},
		{3600000, "1h0m0s"},
	}

	for _, test := range tests {
		result := FormatDuration(test.ms)
		assert.Equal(t, test.expected, result, "Milliseconds: %d", test.ms)
	}
}

func TestNormalizePattern(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"*.js", "*.js"},
		{"**/*.go", "**/*.go"},
		{"./src/**/*.ts", "src/**/*.ts"},
		{"../parent/*.py", "../parent/*.py"},
		{"/absolute/path/*.txt", "/absolute/path/*.txt"},
	}

	for _, test := range tests {
		result := NormalizePattern(test.input)
		assert.Equal(t, test.expected, result, "Input: %s", test.input)
	}
}

// TODO: Fix CalculateScore test logic - penalty calculation needs review
func TestCalculateScore(t *testing.T) {
	tests := []struct {
		total    int
		critical int
		errors   int
		warnings int
		expected float64
	}{
		{0, 0, 0, 0, 100.0},  // No issues
		{10, 0, 0, 10, 90.0}, // Only warnings: 100 - (0*30 + 0*5 + 10*1) = 90
		{10, 0, 5, 5, 70.0},  // Errors and warnings: 100 - (0*30 + 5*5 + 5*1) = 70
		{10, 2, 3, 5, 20.0},  // Mix of all: 100 - (2*30 + 3*5 + 5*1) = 20
		{1, 1, 0, 0, 70.0},   // Only critical: 100 - (1*30 + 0*5 + 0*1) = 70
	}

	for _, test := range tests {
		result := CalculateScore(test.total, test.critical, test.errors, test.warnings)
		assert.InDelta(t, test.expected, result, 0.1,
			"Total: %d, Critical: %d, Errors: %d, Warnings: %d",
			test.total, test.critical, test.errors, test.warnings)
	}
}

func TestGetGrade(t *testing.T) {
	tests := []struct {
		score    float64
		expected string
	}{
		{100.0, "A+"},
		{95.0, "A"},
		{85.0, "B"},
		{75.0, "C"},
		{65.0, "D"},
		{50.0, "F"},
		{0.0, "F"},
	}

	for _, test := range tests {
		result := GetGrade(test.score)
		assert.Equal(t, test.expected, result, "Score: %.1f", test.score)
	}
}

// Helper function to create test files
func createTestFile(path, content string) error {
	// Ensure directory exists
	dir := filepath.Dir(path)
	if err := EnsureDir(dir); err != nil {
		return err
	}
	// Create the actual file
	return os.WriteFile(path, []byte(content), 0644)
}

// Benchmark tests
func BenchmarkTruncateString(b *testing.B) {
	longString := "This is a very long string that will be truncated in the benchmark test"

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		TruncateString(longString, 50)
	}
}

func BenchmarkHash(b *testing.B) {
	testString := "This is a test string for hashing benchmark"

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		Hash(testString)
	}
}

func BenchmarkUniqueStrings(b *testing.B) {
	testSlice := []string{"a", "b", "c", "a", "d", "b", "e", "c", "f", "a"}

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		UniqueStrings(testSlice)
	}
}
