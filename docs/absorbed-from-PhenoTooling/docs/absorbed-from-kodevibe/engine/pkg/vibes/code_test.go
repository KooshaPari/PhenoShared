package vibes

import (
	"testing"

	"github.com/stretchr/testify/assert"

	"kodevibe/internal/models"
)

func TestNewCodeChecker(t *testing.T) {
	checker := NewCodeChecker()

	assert.NotNil(t, checker)
	assert.Equal(t, "CodeVibe", checker.Name())
	assert.Equal(t, models.VibeTypeCode, checker.Type())
	assert.Equal(t, 50, checker.maxFunctionLength)
	assert.Equal(t, 4, checker.maxNestingDepth)
	assert.Equal(t, 120, checker.maxLineLength)
	assert.Equal(t, 10, checker.complexityThreshold)
}

func TestCodeChecker_Configure(t *testing.T) {
	checker := NewCodeChecker()

	config := models.VibeConfig{
		Enabled: true,
		Settings: map[string]interface{}{
			"max_function_length":  30,
			"max_nesting_depth":    3,
			"max_line_length":      100,
			"complexity_threshold": 8,
		},
	}

	err := checker.Configure(config)
	assert.NoError(t, err)
	assert.Equal(t, 30, checker.maxFunctionLength)
	assert.Equal(t, 3, checker.maxNestingDepth)
	assert.Equal(t, 100, checker.maxLineLength)
	assert.Equal(t, 8, checker.complexityThreshold)
}

func TestCodeChecker_Supports(t *testing.T) {
	checker := NewCodeChecker()

	tests := []struct {
		filename string
		expected bool
	}{
		{"test.js", true},
		{"test.py", true},
		{"test.go", true},
		{"test.java", true},
		{"test.cpp", true},
		{"test.rs", true},
		{"test.txt", false},
		{"image.png", false},
	}

	for _, test := range tests {
		result := checker.Supports(test.filename)
		assert.Equal(t, test.expected, result, "File: %s", test.filename)
	}
}

func TestCodeChecker_Check_JavaScriptIssues(t *testing.T) {
	checker := NewCodeChecker()

	// Test individual methods directly since we need to mock file I/O
	tempFile := "test.js"

	// For now, we'll test the individual methods directly since we need to mock file I/O
	// Test checkLine method
	issues := checker.checkLine(tempFile, "var x = 1;", 1)
	assert.Greater(t, len(issues), 0)

	hasVarIssue := false
	for _, issue := range issues {
		if issue.Rule == "no-var" {
			hasVarIssue = true
		}
	}
	assert.True(t, hasVarIssue)

	// Test console.log detection
	issues = checker.checkLine(tempFile, `console.log("test");`, 2)
	hasConsoleIssue := false
	for _, issue := range issues {
		if issue.Rule == "no-console-log" {
			hasConsoleIssue = true
		}
	}
	assert.True(t, hasConsoleIssue)

	// Test strict equality
	issues = checker.checkLine(tempFile, "if (x == 1) {", 3)
	hasEqualityIssue := false
	for _, issue := range issues {
		if issue.Rule == "strict-equality" {
			hasEqualityIssue = true
		}
	}
	assert.True(t, hasEqualityIssue)
}

func TestCodeChecker_Check_PythonIssues(t *testing.T) {
	checker := NewCodeChecker()

	// Test print statement detection
	issues := checker.checkLine("test.py", `print("Hello world")`, 1)

	hasPrintIssue := false
	for _, issue := range issues {
		if issue.Rule == "no-print" {
			hasPrintIssue = true
		}
	}
	assert.True(t, hasPrintIssue)
}

func TestCodeChecker_Check_GoIssues(t *testing.T) {
	checker := NewCodeChecker()

	// Test context.TODO() detection
	issues := checker.checkLine("test.go", "ctx := context.TODO()", 1)

	hasContextTodoIssue := false
	for _, issue := range issues {
		if issue.Rule == "no-context-todo" {
			hasContextTodoIssue = true
		}
	}
	assert.True(t, hasContextTodoIssue)

	// Test panic detection
	issues = checker.checkLine("test.go", "panic(\"error\")", 2)

	hasPanicIssue := false
	for _, issue := range issues {
		if issue.Rule == "no-panic" {
			hasPanicIssue = true
		}
	}
	assert.True(t, hasPanicIssue)
}

func TestCodeChecker_Check_JavaIssues(t *testing.T) {
	checker := NewCodeChecker()

	// Test System.out.println detection
	issues := checker.checkLine("test.java", `System.out.println("Hello");`, 1)

	hasSystemOutIssue := false
	for _, issue := range issues {
		if issue.Rule == "no-system-out" {
			hasSystemOutIssue = true
		}
	}
	assert.True(t, hasSystemOutIssue)
}

func TestCodeChecker_Check_LineLength(t *testing.T) {
	checker := NewCodeChecker()
	checker.maxLineLength = 50

	shortLine := "short line"
	longLine := "this is a very long line that exceeds the maximum length configured for the checker"

	// Test short line
	issues := checker.checkLine("test.js", shortLine, 1)
	hasLineLengthIssue := false
	for _, issue := range issues {
		if issue.Rule == "line-length" {
			hasLineLengthIssue = true
		}
	}
	assert.False(t, hasLineLengthIssue)

	// Test long line
	issues = checker.checkLine("test.js", longLine, 2)
	hasLineLengthIssue = false
	for _, issue := range issues {
		if issue.Rule == "line-length" {
			hasLineLengthIssue = true
		}
	}
	assert.True(t, hasLineLengthIssue)
}

func TestCodeChecker_Check_TODOComments(t *testing.T) {
	checker := NewCodeChecker()

	tests := []struct {
		line     string
		expected bool
	}{
		{"// TODO: implement this", true},
		{"# FIXME: broken code", true},
		{"/* HACK: temporary solution */", true},
		{"// XXX: this is bad", true},
		{"# BUG: needs fixing", true},
		{"// This is a normal comment", false},
		{"const x = 1;", false},
	}

	for _, test := range tests {
		issues := checker.checkLine("test.js", test.line, 1)

		hasTodoIssue := false
		for _, issue := range issues {
			if issue.Rule == "todo-comments" {
				hasTodoIssue = true
				break
			}
		}

		assert.Equal(t, test.expected, hasTodoIssue, "Line: %s", test.line)
	}
}

func TestCodeChecker_Check_CommentedOutCode(t *testing.T) {
	checker := NewCodeChecker()

	tests := []struct {
		line     string
		expected bool
	}{
		{"// var x = 1;", true},
		{"# print('hello')", true},
		{"/* return x; */", true},
		{"// This is a comment", false},
		{"# Just a comment", false},
		{"const x = 1;", false},
	}

	for _, test := range tests {
		issues := checker.checkLine("test.js", test.line, 1)

		hasCommentedCodeIssue := false
		for _, issue := range issues {
			if issue.Rule == "commented-code" {
				hasCommentedCodeIssue = true
				break
			}
		}

		assert.Equal(t, test.expected, hasCommentedCodeIssue, "Line: %s", test.line)
	}
}

func TestCodeChecker_Check_MagicNumbers(t *testing.T) {
	checker := NewCodeChecker()

	tests := []struct {
		line        string
		expectIssue bool
	}{
		{"const x = 42;", true},       // Magic number
		{"const y = 0;", false},       // Common number
		{"const z = 1;", false},       // Common number
		{"const a = 10;", false},      // Common number
		{"const b = 999;", true},      // Magic number
		{"// Port 8080", false},       // In comment
		{"const port = 3000;", false}, // Common number
	}

	for _, test := range tests {
		issues := checker.checkLine("test.js", test.line, 1)

		hasMagicNumberIssue := false
		for _, issue := range issues {
			if issue.Rule == "magic-numbers" {
				hasMagicNumberIssue = true
				break
			}
		}

		assert.Equal(t, test.expectIssue, hasMagicNumberIssue, "Line: %s", test.line)
	}
}

func TestCodeChecker_countFunctionLines(t *testing.T) {
	checker := NewCodeChecker()

	lines := []string{
		"function test() {",
		"    var x = 1;",
		"    if (x > 0) {",
		"        console.log(x);",
		"    }",
		"    return x;",
		"}",
		"",
		"function another() {",
		"    return 42;",
		"}",
	}

	// Count lines for first function
	count := checker.countFunctionLines(lines, 0)
	assert.Equal(t, 7, count)

	// Count lines for second function
	count = checker.countFunctionLines(lines, 8)
	assert.Equal(t, 3, count)
}

func TestCodeChecker_calculateComplexity(t *testing.T) {
	checker := NewCodeChecker()

	// Simple function
	simpleLines := []string{
		"function simple() {",
		"    return 42;",
		"}",
	}
	complexity := checker.calculateComplexity(simpleLines)
	assert.Equal(t, 1, complexity) // Base complexity

	// Complex function
	complexLines := []string{
		"function complex(x) {",
		"    if (x > 0) {",
		"        for (let i = 0; i < x; i++) {",
		"            if (i % 2 === 0 && i > 10) {",
		"                console.log(i);",
		"            } else {",
		"                console.log('odd');",
		"            }",
		"        }",
		"    }",
		"    return x > 0 ? x : -x;",
		"}",
	}
	complexity = checker.calculateComplexity(complexLines)
	assert.GreaterOrEqual(t, complexity, 5) // Should be complex
}

func TestCodeChecker_isCommonNumber(t *testing.T) {
	checker := NewCodeChecker()

	tests := []struct {
		number   string
		expected bool
	}{
		{"0", false},   // Not checked by magic number pattern
		{"1", false},   // Not checked by magic number pattern
		{"2", true},    // Common
		{"10", true},   // Common
		{"100", true},  // Common
		{"42", false},  // Not common
		{"999", false}, // Not common
	}

	for _, test := range tests {
		result := checker.isCommonNumber(test.number)
		assert.Equal(t, test.expected, result, "Number: %s", test.number)
	}
}

// Benchmark tests
func BenchmarkCodeChecker_checkLine(b *testing.B) {
	checker := NewCodeChecker()
	testLine := `var x = 1; console.log("test"); if (x == 1) { return x; }`

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		checker.checkLine("test.js", testLine, 1)
	}
}

func BenchmarkCodeChecker_calculateComplexity(b *testing.B) {
	checker := NewCodeChecker()
	lines := []string{
		"function complex(x) {",
		"    if (x > 0) {",
		"        for (let i = 0; i < x; i++) {",
		"            if (i % 2 === 0 && i > 10) {",
		"                console.log(i);",
		"            } else {",
		"                console.log('odd');",
		"            }",
		"        }",
		"    }",
		"    return x > 0 ? x : -x;",
		"}",
	}

	b.ResetTimer()

	for i := 0; i < b.N; i++ {
		checker.calculateComplexity(lines)
	}
}
