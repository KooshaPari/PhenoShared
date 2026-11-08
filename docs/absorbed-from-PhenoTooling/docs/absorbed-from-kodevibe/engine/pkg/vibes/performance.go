package vibes

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"kodevibe/internal/models"
	"kodevibe/internal/utils"
)

// PerformanceChecker implements performance-related checks
type PerformanceChecker struct {
	config           models.VibeConfig
	maxBundleSize    int64
	performanceRules map[string]*PerformanceRules
}

// PerformanceRules contains language-specific performance rules
type PerformanceRules struct {
	Extensions         []string
	AntiPatterns       []*PerformanceAntiPattern
	BlockingOperations []*regexp.Regexp
	MemoryLeakPatterns []*regexp.Regexp
	NestedLoopPatterns []*regexp.Regexp
}

// PerformanceAntiPattern represents a performance anti-pattern
type PerformanceAntiPattern struct {
	Name          string
	Pattern       *regexp.Regexp
	Description   string
	Severity      models.SeverityLevel
	FixSuggestion string
	Confidence    float64
}

// NewPerformanceChecker creates a new performance checker
func NewPerformanceChecker() *PerformanceChecker {
	checker := &PerformanceChecker{
		maxBundleSize:    2 * 1024 * 1024, // 2MB
		performanceRules: make(map[string]*PerformanceRules),
	}

	checker.initializePerformanceRules()
	return checker
}

// Name returns the checker name
func (pc *PerformanceChecker) Name() string {
	return "PerformanceVibe"
}

// Type returns the vibe type
func (pc *PerformanceChecker) Type() models.VibeType {
	return models.VibeTypePerformance
}

// Configure configures the performance checker
func (pc *PerformanceChecker) Configure(config models.VibeConfig) error {
	pc.config = config

	if maxBundle, exists := config.Settings["max_bundle_size"]; exists {
		if maxBundleStr, ok := maxBundle.(string); ok {
			size, err := utils.ParseSize(maxBundleStr)
			if err == nil {
				pc.maxBundleSize = size
			}
		}
	}

	return nil
}

// Supports returns true if the checker supports the given file
func (pc *PerformanceChecker) Supports(filename string) bool {
	ext := strings.ToLower(filepath.Ext(filename))
	supportedExtensions := []string{
		".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".java", ".c", ".cpp",
		".rb", ".php", ".cs", ".sql", ".html", ".css",
	}

	for _, supportedExt := range supportedExtensions {
		if ext == supportedExt {
			return true
		}
	}

	return false
}

// Check performs performance checks on the provided files
func (pc *PerformanceChecker) Check(ctx context.Context, files []string) ([]models.Issue, error) {
	var issues []models.Issue

	for _, file := range files {
		if !pc.Supports(file) {
			continue
		}

		fileIssues, err := pc.checkFile(file)
		if err != nil {
			continue
		}

		issues = append(issues, fileIssues...)

		select {
		case <-ctx.Done():
			return issues, ctx.Err()
		default:
		}
	}

	return issues, nil
}

// checkFile performs performance checks on a single file
func (pc *PerformanceChecker) checkFile(filename string) ([]models.Issue, error) {
	var issues []models.Issue

	// Check file size first
	if fileInfo, err := os.Stat(filename); err == nil {
		if fileInfo.Size() > pc.maxBundleSize {
			ext := strings.ToLower(filepath.Ext(filename))
			if ext == ".js" || ext == ".css" {
				issue := models.Issue{
					Type:          models.VibeTypePerformance,
					Severity:      models.SeverityWarning,
					Title:         "Large bundle file",
					Message:       fmt.Sprintf("File size (%s) exceeds recommended maximum (%s)", utils.FormatSize(fileInfo.Size()), utils.FormatSize(pc.maxBundleSize)),
					File:          filename,
					Line:          1,
					Rule:          "large-bundle-size",
					Fixable:       true,
					FixSuggestion: "Consider code splitting or minification",
					Confidence:    1.0,
				}
				issues = append(issues, issue)
			}
		}
	}

	file, err := os.Open(filename)
	if err != nil {
		return nil, fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	lines := []string{}
	lineNumber := 0

	for scanner.Scan() {
		lineNumber++
		line := scanner.Text()
		lines = append(lines, line)

		lineIssues := pc.checkLine(filename, line, lineNumber)
		issues = append(issues, lineIssues...)
	}

	if err := scanner.Err(); err != nil {
		return issues, fmt.Errorf("error reading file: %w", err)
	}

	multiLineIssues := pc.checkMultiLine(filename, lines)
	issues = append(issues, multiLineIssues...)

	return issues, nil
}

// checkLine performs checks on a single line
func (pc *PerformanceChecker) checkLine(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue
	ext := strings.ToLower(filepath.Ext(filename))

	switch ext {
	case ".js", ".jsx", ".ts", ".tsx":
		issues = append(issues, pc.checkJavaScriptLine(filename, line, lineNumber)...)
	case ".py":
		issues = append(issues, pc.checkPythonLine(filename, line, lineNumber)...)
	case ".go":
		issues = append(issues, pc.checkGoLine(filename, line, lineNumber)...)
	case ".sql":
		issues = append(issues, pc.checkSQLLine(filename, line, lineNumber)...)
	}

	return issues
}

// checkMultiLine performs multi-line performance checks
func (pc *PerformanceChecker) checkMultiLine(filename string, lines []string) []models.Issue {
	var issues []models.Issue

	// Check for nested loops
	nestedLoopIssues := pc.checkNestedLoops(filename, lines)
	issues = append(issues, nestedLoopIssues...)

	// Check for N+1 query patterns
	n1QueryIssues := pc.checkN1Queries(filename, lines)
	issues = append(issues, n1QueryIssues...)

	return issues
}

// checkJavaScriptLine performs JavaScript-specific performance checks
func (pc *PerformanceChecker) checkJavaScriptLine(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Check for synchronous file operations
	syncPatterns := []*regexp.Regexp{
		regexp.MustCompile(`readFileSync\s*\(`),
		regexp.MustCompile(`writeFileSync\s*\(`),
		regexp.MustCompile(`existsSync\s*\(`),
	}

	for _, pattern := range syncPatterns {
		if pattern.MatchString(line) {
			issue := models.Issue{
				Type:          models.VibeTypePerformance,
				Severity:      models.SeverityWarning,
				Title:         "Synchronous file operation",
				Message:       "Synchronous file operations can block the event loop",
				File:          filename,
				Line:          lineNumber,
				Rule:          "sync-file-operations",
				Context:       utils.TruncateString(line, 100),
				Fixable:       true,
				FixSuggestion: "Use asynchronous alternatives (readFile, writeFile, access)",
				Confidence:    0.9,
			}
			issues = append(issues, issue)
		}
	}

	// Check for inefficient array operations
	if regexp.MustCompile(`\.forEach\s*\([^)]*\.push\(`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypePerformance,
			Severity:      models.SeverityInfo,
			Title:         "Inefficient array operation",
			Message:       "Consider using map() instead of forEach + push",
			File:          filename,
			Line:          lineNumber,
			Rule:          "inefficient-array-ops",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Use array.map() for transformations",
			Confidence:    0.8,
		}
		issues = append(issues, issue)
	}

	// Check for DOM queries in loops (potential performance issue)
	if regexp.MustCompile(`document\.(getElementById|querySelector|querySelectorAll)`).MatchString(line) {
		// This would need more context to determine if it's in a loop
		issue := models.Issue{
			Type:          models.VibeTypePerformance,
			Severity:      models.SeverityInfo,
			Title:         "DOM query detected",
			Message:       "Cache DOM queries outside of loops for better performance",
			File:          filename,
			Line:          lineNumber,
			Rule:          "dom-query-performance",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Cache DOM elements outside loops",
			Confidence:    0.6,
		}
		issues = append(issues, issue)
	}

	// Check for potential memory leaks
	memoryLeakPatterns := []*regexp.Regexp{
		regexp.MustCompile(`addEventListener\s*\(`),
		regexp.MustCompile(`setInterval\s*\(`),
		regexp.MustCompile(`setTimeout\s*\([^,]+,\s*0\)`), // setTimeout with 0 delay
	}

	for _, pattern := range memoryLeakPatterns {
		if pattern.MatchString(line) {
			issue := models.Issue{
				Type:          models.VibeTypePerformance,
				Severity:      models.SeverityWarning,
				Title:         "Potential memory leak",
				Message:       "Ensure event listeners and timers are properly cleaned up",
				File:          filename,
				Line:          lineNumber,
				Rule:          "memory-leak-potential",
				Context:       utils.TruncateString(line, 100),
				Fixable:       false,
				FixSuggestion: "Add corresponding removeEventListener or clearInterval/clearTimeout",
				Confidence:    0.7,
			}
			issues = append(issues, issue)
		}
	}

	return issues
}

// checkPythonLine performs Python-specific performance checks
func (pc *PerformanceChecker) checkPythonLine(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Check for inefficient string concatenation
	if regexp.MustCompile(`\+=\s*['""]`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypePerformance,
			Severity:      models.SeverityWarning,
			Title:         "Inefficient string concatenation",
			Message:       "String concatenation with += in loops is inefficient",
			File:          filename,
			Line:          lineNumber,
			Rule:          "string-concat-performance",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Use join() for multiple string concatenations",
			Confidence:    0.8,
		}
		issues = append(issues, issue)
	}

	// Check for global variable access in loops
	if regexp.MustCompile(`global\s+\w+`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypePerformance,
			Severity:      models.SeverityInfo,
			Title:         "Global variable access",
			Message:       "Global variable access can be slower than local variables",
			File:          filename,
			Line:          lineNumber,
			Rule:          "global-variable-performance",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Consider using local variables when possible",
			Confidence:    0.6,
		}
		issues = append(issues, issue)
	}

	return issues
}

// checkGoLine performs Go-specific performance checks
func (pc *PerformanceChecker) checkGoLine(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Check for string concatenation in loops
	if regexp.MustCompile(`\+=.*[""]\s*\+`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypePerformance,
			Severity:      models.SeverityWarning,
			Title:         "Inefficient string concatenation",
			Message:       "Use strings.Builder for efficient string concatenation",
			File:          filename,
			Line:          lineNumber,
			Rule:          "string-concat-performance",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Use strings.Builder or bytes.Buffer",
			Confidence:    0.8,
		}
		issues = append(issues, issue)
	}

	// Check for defer in loops
	if regexp.MustCompile(`defer\s+`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypePerformance,
			Severity:      models.SeverityWarning,
			Title:         "Defer in potential loop",
			Message:       "Defer statements in loops can cause memory buildup",
			File:          filename,
			Line:          lineNumber,
			Rule:          "defer-in-loop",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Move defer outside loop or use explicit cleanup",
			Confidence:    0.7,
		}
		issues = append(issues, issue)
	}

	return issues
}

// checkSQLLine performs SQL-specific performance checks
func (pc *PerformanceChecker) checkSQLLine(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Check for SELECT *
	if regexp.MustCompile(`(?i)SELECT\s+\*\s+FROM`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypePerformance,
			Severity:      models.SeverityWarning,
			Title:         "SELECT * query",
			Message:       "SELECT * can be inefficient, specify needed columns",
			File:          filename,
			Line:          lineNumber,
			Rule:          "select-star-performance",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Specify only the columns you need",
			Confidence:    0.8,
		}
		issues = append(issues, issue)
	}

	// Check for missing WHERE clause
	if regexp.MustCompile(`(?i)DELETE\s+FROM\s+\w+\s*$`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypePerformance,
			Severity:      models.SeverityError,
			Title:         "DELETE without WHERE",
			Message:       "DELETE statement without WHERE clause will delete all rows",
			File:          filename,
			Line:          lineNumber,
			Rule:          "delete-without-where",
			Context:       utils.TruncateString(line, 100),
			Fixable:       false,
			FixSuggestion: "Add WHERE clause to limit deletion scope",
			Confidence:    0.95,
		}
		issues = append(issues, issue)
	}

	return issues
}

// checkNestedLoops detects nested loops that could cause O(n²) complexity
func (pc *PerformanceChecker) checkNestedLoops(filename string, lines []string) []models.Issue {
	var issues []models.Issue

	loopPatterns := []*regexp.Regexp{
		regexp.MustCompile(`\bfor\b`),
		regexp.MustCompile(`\bwhile\b`),
		regexp.MustCompile(`\.forEach\b`),
		regexp.MustCompile(`\.map\b`),
		regexp.MustCompile(`\.filter\b`),
	}

	for i, line := range lines {
		for _, pattern := range loopPatterns {
			if pattern.MatchString(line) {
				// Check for nested loops in the next few lines
				for j := i + 1; j < len(lines) && j < i+10; j++ {
					for _, nestedPattern := range loopPatterns {
						if nestedPattern.MatchString(lines[j]) {
							issue := models.Issue{
								Type:          models.VibeTypePerformance,
								Severity:      models.SeverityWarning,
								Title:         "Nested loops detected",
								Message:       "Nested loops can cause O(n²) complexity",
								File:          filename,
								Line:          i + 1,
								Rule:          "nested-loops",
								Context:       utils.TruncateString(line, 100),
								Fixable:       true,
								FixSuggestion: "Consider algorithm optimization or caching",
								Confidence:    0.8,
							}
							issues = append(issues, issue)
							goto nextLine
						}
					}
				}
			nextLine:
			}
		}
	}

	return issues
}

// checkN1Queries detects potential N+1 query patterns
func (pc *PerformanceChecker) checkN1Queries(filename string, lines []string) []models.Issue {
	var issues []models.Issue

	// Look for database queries inside loops
	queryPatterns := []*regexp.Regexp{
		regexp.MustCompile(`(?i)SELECT.*FROM`),
		regexp.MustCompile(`(?i)INSERT.*INTO`),
		regexp.MustCompile(`(?i)UPDATE.*SET`),
		regexp.MustCompile(`(?i)DELETE.*FROM`),
		regexp.MustCompile(`\.query\s*\(`),
		regexp.MustCompile(`\.find\s*\(`),
		regexp.MustCompile(`\.findOne\s*\(`),
	}

	loopPatterns := []*regexp.Regexp{
		regexp.MustCompile(`\bfor\b`),
		regexp.MustCompile(`\bwhile\b`),
		regexp.MustCompile(`\.forEach\b`),
		regexp.MustCompile(`\.map\b`),
	}

	for i, line := range lines {
		for _, loopPattern := range loopPatterns {
			if loopPattern.MatchString(line) {
				// Check for queries in the loop body
				for j := i + 1; j < len(lines) && j < i+20; j++ {
					for _, queryPattern := range queryPatterns {
						if queryPattern.MatchString(lines[j]) {
							issue := models.Issue{
								Type:          models.VibeTypePerformance,
								Severity:      models.SeverityError,
								Title:         "Potential N+1 query",
								Message:       "Database query inside loop can cause N+1 query problem",
								File:          filename,
								Line:          j + 1,
								Rule:          "n-plus-one-query",
								Context:       utils.TruncateString(lines[j], 100),
								Fixable:       true,
								FixSuggestion: "Use batch queries or eager loading",
								Confidence:    0.9,
							}
							issues = append(issues, issue)
						}
					}
				}
			}
		}
	}

	return issues
}

// initializePerformanceRules initializes performance rules for different languages
func (pc *PerformanceChecker) initializePerformanceRules() {
	// JavaScript/TypeScript rules
	jsRules := &PerformanceRules{
		Extensions: []string{".js", ".jsx", ".ts", ".tsx"},
		BlockingOperations: []*regexp.Regexp{
			regexp.MustCompile(`readFileSync\s*\(`),
			regexp.MustCompile(`writeFileSync\s*\(`),
			regexp.MustCompile(`execSync\s*\(`),
		},
		MemoryLeakPatterns: []*regexp.Regexp{
			regexp.MustCompile(`addEventListener\s*\(`),
			regexp.MustCompile(`setInterval\s*\(`),
			regexp.MustCompile(`new\s+Array\s*\(\s*\d+\s*\)`),
		},
	}
	pc.performanceRules[".js"] = jsRules
	pc.performanceRules[".jsx"] = jsRules
	pc.performanceRules[".ts"] = jsRules
	pc.performanceRules[".tsx"] = jsRules
}
