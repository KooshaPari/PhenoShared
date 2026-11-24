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

// CodeChecker implements code quality checks
type CodeChecker struct {
	config              models.VibeConfig
	maxFunctionLength   int
	maxNestingDepth     int
	maxLineLength       int
	languageRules       map[string]*LanguageRules
	complexityThreshold int
}

// LanguageRules contains language-specific code quality rules
type LanguageRules struct {
	Extensions       []string
	FunctionPatterns []*regexp.Regexp
	ClassPatterns    []*regexp.Regexp
	CommentPatterns  []*regexp.Regexp
	ImportPatterns   []*regexp.Regexp
	VariablePatterns []*regexp.Regexp
	DeadCodePatterns []*regexp.Regexp
	AntiPatterns     []*AntiPattern
	StyleRules       []*StyleRule
}

// AntiPattern represents a code anti-pattern
type AntiPattern struct {
	Name          string
	Pattern       *regexp.Regexp
	Description   string
	Severity      models.SeverityLevel
	FixSuggestion string
}

// StyleRule represents a code style rule
type StyleRule struct {
	Name          string
	Pattern       *regexp.Regexp
	Description   string
	Severity      models.SeverityLevel
	FixSuggestion string
}

// NewCodeChecker creates a new code quality checker
func NewCodeChecker() *CodeChecker {
	checker := &CodeChecker{
		maxFunctionLength:   50,
		maxNestingDepth:     4,
		maxLineLength:       120,
		complexityThreshold: 10,
		languageRules:       make(map[string]*LanguageRules),
	}

	checker.initializeLanguageRules()
	return checker
}

// Name returns the checker name
func (cc *CodeChecker) Name() string {
	return "CodeVibe"
}

// Type returns the vibe type
func (cc *CodeChecker) Type() models.VibeType {
	return models.VibeTypeCode
}

// Configure configures the code checker
func (cc *CodeChecker) Configure(config models.VibeConfig) error {
	cc.config = config

	// Configure thresholds from settings
	if maxFunc, exists := config.Settings["max_function_length"]; exists {
		if maxFuncInt, ok := maxFunc.(int); ok {
			cc.maxFunctionLength = maxFuncInt
		}
	}

	if maxNest, exists := config.Settings["max_nesting_depth"]; exists {
		if maxNestInt, ok := maxNest.(int); ok {
			cc.maxNestingDepth = maxNestInt
		}
	}

	if maxLine, exists := config.Settings["max_line_length"]; exists {
		if maxLineInt, ok := maxLine.(int); ok {
			cc.maxLineLength = maxLineInt
		}
	}

	if complexity, exists := config.Settings["complexity_threshold"]; exists {
		if complexityInt, ok := complexity.(int); ok {
			cc.complexityThreshold = complexityInt
		}
	}

	return nil
}

// Supports returns true if the checker supports the given file
func (cc *CodeChecker) Supports(filename string) bool {
	ext := strings.ToLower(filepath.Ext(filename))
	supportedExtensions := []string{
		".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".java", ".c", ".cpp", ".h", ".hpp",
		".rb", ".php", ".sh", ".bash", ".zsh", ".rs", ".kt", ".swift", ".scala",
		".cs", ".vb", ".dart", ".lua", ".r", ".matlab", ".perl", ".groovy",
	}

	for _, supportedExt := range supportedExtensions {
		if ext == supportedExt {
			return true
		}
	}

	return false
}

// Check performs code quality checks on the provided files
func (cc *CodeChecker) Check(ctx context.Context, files []string) ([]models.Issue, error) {
	var issues []models.Issue

	for _, file := range files {
		if !cc.Supports(file) {
			continue
		}

		fileIssues, err := cc.checkFile(file)
		if err != nil {
			// Log error but continue with other files
			continue
		}

		issues = append(issues, fileIssues...)

		// Check context cancellation
		select {
		case <-ctx.Done():
			return issues, ctx.Err()
		default:
		}
	}

	return issues, nil
}

// checkFile performs code quality checks on a single file
func (cc *CodeChecker) checkFile(filename string) ([]models.Issue, error) {
	var issues []models.Issue

	file, err := os.Open(filename)
	if err != nil {
		return nil, fmt.Errorf("failed to open file: %w", err)
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	lines := []string{}
	lineNumber := 0

	// Read all lines
	for scanner.Scan() {
		lineNumber++
		line := scanner.Text()
		lines = append(lines, line)

		// Check individual line issues
		lineIssues := cc.checkLine(filename, line, lineNumber)
		issues = append(issues, lineIssues...)
	}

	if err := scanner.Err(); err != nil {
		return issues, fmt.Errorf("error reading file: %w", err)
	}

	// Check multi-line issues
	multiLineIssues := cc.checkMultiLine(filename, lines)
	issues = append(issues, multiLineIssues...)

	return issues, nil
}

// checkLine performs checks on a single line
func (cc *CodeChecker) checkLine(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Check line length
	if len(line) > cc.maxLineLength {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityWarning,
			Title:         "Line too long",
			Message:       fmt.Sprintf("Line length (%d) exceeds maximum (%d)", len(line), cc.maxLineLength),
			File:          filename,
			Line:          lineNumber,
			Rule:          "line-length",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Break long lines into multiple lines",
			Confidence:    1.0,
		}
		issues = append(issues, issue)
	}

	// Check for TODO/FIXME comments
	todoPattern := regexp.MustCompile(`(?i)\b(TODO|FIXME|HACK|XXX|BUG)\b`)
	if todoPattern.MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityInfo,
			Title:         "TODO/FIXME comment found",
			Message:       "TODO/FIXME comments should be tracked in issues",
			File:          filename,
			Line:          lineNumber,
			Rule:          "todo-comments",
			Context:       utils.TruncateString(line, 100),
			Fixable:       false,
			FixSuggestion: "Create an issue to track this task",
			Confidence:    1.0,
		}
		issues = append(issues, issue)
	}

	// Check for commented-out code
	if cc.isCommentedOutCode(line) {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityWarning,
			Title:         "Commented-out code detected",
			Message:       "Commented-out code should be removed",
			File:          filename,
			Line:          lineNumber,
			Rule:          "commented-code",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Remove commented-out code or use version control",
			Confidence:    0.8,
		}
		issues = append(issues, issue)
	}

	// Check for magic numbers
	magicNumberIssues := cc.checkMagicNumbers(filename, line, lineNumber)
	issues = append(issues, magicNumberIssues...)

	// Check language-specific issues
	langIssues := cc.checkLanguageSpecific(filename, line, lineNumber)
	issues = append(issues, langIssues...)

	return issues
}

// checkMultiLine performs checks that require multiple lines
func (cc *CodeChecker) checkMultiLine(filename string, lines []string) []models.Issue {
	var issues []models.Issue

	// Check function length
	functionIssues := cc.checkFunctionLength(filename, lines)
	issues = append(issues, functionIssues...)

	// Check nesting depth
	nestingIssues := cc.checkNestingDepth(filename, lines)
	issues = append(issues, nestingIssues...)

	// Check for duplicate code
	duplicateIssues := cc.checkDuplicateCode(filename, lines)
	issues = append(issues, duplicateIssues...)

	// Check cyclomatic complexity
	complexityIssues := cc.checkComplexity(filename, lines)
	issues = append(issues, complexityIssues...)

	return issues
}

// checkFunctionLength checks for functions that are too long
func (cc *CodeChecker) checkFunctionLength(filename string, lines []string) []models.Issue {
	var issues []models.Issue
	ext := strings.ToLower(filepath.Ext(filename))

	// Get language rules
	rules := cc.getLanguageRules(ext)
	if rules == nil {
		return issues
	}

	for _, functionPattern := range rules.FunctionPatterns {
		for i, line := range lines {
			if functionPattern.MatchString(line) {
				// Found function start, count lines until end
				functionLength := cc.countFunctionLines(lines, i)
				if functionLength > cc.maxFunctionLength {
					issue := models.Issue{
						Type:          models.VibeTypeCode,
						Severity:      models.SeverityWarning,
						Title:         "Function too long",
						Message:       fmt.Sprintf("Function has %d lines, exceeds maximum of %d", functionLength, cc.maxFunctionLength),
						File:          filename,
						Line:          i + 1,
						Rule:          "function-length",
						Context:       utils.TruncateString(line, 100),
						Fixable:       true,
						FixSuggestion: "Break long functions into smaller, more focused functions",
						Confidence:    0.9,
					}
					issues = append(issues, issue)
				}
			}
		}
	}

	return issues
}

// checkNestingDepth checks for excessive nesting
func (cc *CodeChecker) checkNestingDepth(filename string, lines []string) []models.Issue {
	var issues []models.Issue

	maxDepth := 0
	currentDepth := 0
	maxDepthLine := 0

	for i, line := range lines {
		// Count opening braces/keywords that increase nesting
		if cc.increasesNesting(line) {
			currentDepth++
			if currentDepth > maxDepth {
				maxDepth = currentDepth
				maxDepthLine = i + 1
			}
		}

		// Count closing braces that decrease nesting
		if cc.decreasesNesting(line) {
			currentDepth--
			if currentDepth < 0 {
				currentDepth = 0
			}
		}
	}

	if maxDepth > cc.maxNestingDepth {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityWarning,
			Title:         "Excessive nesting depth",
			Message:       fmt.Sprintf("Maximum nesting depth (%d) exceeds recommended limit (%d)", maxDepth, cc.maxNestingDepth),
			File:          filename,
			Line:          maxDepthLine,
			Rule:          "nesting-depth",
			Context:       utils.TruncateString(lines[maxDepthLine-1], 100),
			Fixable:       true,
			FixSuggestion: "Refactor code to reduce nesting using early returns or helper functions",
			Confidence:    0.8,
		}
		issues = append(issues, issue)
	}

	return issues
}

// checkDuplicateCode checks for duplicate code blocks
func (cc *CodeChecker) checkDuplicateCode(filename string, lines []string) []models.Issue {
	var issues []models.Issue

	// Simple duplicate detection - look for identical blocks of 5+ lines
	minBlockSize := 5
	blockMap := make(map[string][]int)

	for i := 0; i <= len(lines)-minBlockSize; i++ {
		block := strings.Join(lines[i:i+minBlockSize], "\n")
		block = cc.normalizeBlock(block)

		if len(strings.TrimSpace(block)) > 20 { // Ignore very small blocks
			blockMap[block] = append(blockMap[block], i+1)
		}
	}

	for block, occurrences := range blockMap {
		if len(occurrences) > 1 {
			for _, lineNum := range occurrences {
				issue := models.Issue{
					Type:          models.VibeTypeCode,
					Severity:      models.SeverityWarning,
					Title:         "Duplicate code detected",
					Message:       fmt.Sprintf("Code block appears %d times in the file", len(occurrences)),
					File:          filename,
					Line:          lineNum,
					Rule:          "duplicate-code",
					Context:       utils.TruncateString(block, 100),
					Fixable:       true,
					FixSuggestion: "Extract duplicate code into a reusable function",
					Confidence:    0.7,
				}
				issues = append(issues, issue)
			}
		}
	}

	return issues
}

// checkComplexity checks cyclomatic complexity
func (cc *CodeChecker) checkComplexity(filename string, lines []string) []models.Issue {
	var issues []models.Issue
	ext := strings.ToLower(filepath.Ext(filename))

	// Get language rules
	rules := cc.getLanguageRules(ext)
	if rules == nil {
		return issues
	}

	for _, functionPattern := range rules.FunctionPatterns {
		for i, line := range lines {
			if functionPattern.MatchString(line) {
				// Calculate complexity for this function
				functionEnd := cc.findFunctionEnd(lines, i)
				complexity := cc.calculateComplexity(lines[i:functionEnd])

				if complexity > cc.complexityThreshold {
					issue := models.Issue{
						Type:          models.VibeTypeCode,
						Severity:      models.SeverityWarning,
						Title:         "High cyclomatic complexity",
						Message:       fmt.Sprintf("Function complexity (%d) exceeds threshold (%d)", complexity, cc.complexityThreshold),
						File:          filename,
						Line:          i + 1,
						Rule:          "cyclomatic-complexity",
						Context:       utils.TruncateString(line, 100),
						Fixable:       true,
						FixSuggestion: "Break complex function into smaller functions",
						Confidence:    0.8,
					}
					issues = append(issues, issue)
				}
			}
		}
	}

	return issues
}

// checkMagicNumbers checks for magic numbers in code
func (cc *CodeChecker) checkMagicNumbers(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Pattern to find numeric literals (excluding 0, 1, -1)
	magicNumberPattern := regexp.MustCompile(`\b(?:[2-9]|[1-9]\d+)\b`)
	matches := magicNumberPattern.FindAllString(line, -1)

	for _, match := range matches {
		// Skip common non-magic numbers
		if cc.isCommonNumber(match) {
			continue
		}

		// Skip if it's in a comment
		if cc.isInComment(line, match) {
			continue
		}

		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityInfo,
			Title:         "Magic number detected",
			Message:       fmt.Sprintf("Magic number '%s' should be replaced with a named constant", match),
			File:          filename,
			Line:          lineNumber,
			Rule:          "magic-numbers",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Replace magic number with a named constant",
			Confidence:    0.6,
		}
		issues = append(issues, issue)
	}

	return issues
}

// checkLanguageSpecific performs language-specific checks
func (cc *CodeChecker) checkLanguageSpecific(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue
	ext := strings.ToLower(filepath.Ext(filename))

	switch ext {
	case ".js", ".jsx", ".ts", ".tsx":
		issues = append(issues, cc.checkJavaScript(filename, line, lineNumber)...)
	case ".py":
		issues = append(issues, cc.checkPython(filename, line, lineNumber)...)
	case ".go":
		issues = append(issues, cc.checkGo(filename, line, lineNumber)...)
	case ".java":
		issues = append(issues, cc.checkJava(filename, line, lineNumber)...)
	}

	return issues
}

// checkJavaScript performs JavaScript-specific checks
func (cc *CodeChecker) checkJavaScript(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Check for console.log statements
	if strings.Contains(line, "console.log(") {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityWarning,
			Title:         "Console.log statement found",
			Message:       "Console.log statements should be removed before production",
			File:          filename,
			Line:          lineNumber,
			Rule:          "no-console-log",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Remove console.log or use a proper logging library",
			Confidence:    1.0,
		}
		issues = append(issues, issue)
	}

	// Check for == instead of ===
	if regexp.MustCompile(`[^!=]==[^=]`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityWarning,
			Title:         "Use strict equality",
			Message:       "Use === instead of == for strict equality comparison",
			File:          filename,
			Line:          lineNumber,
			Rule:          "strict-equality",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Replace == with ===",
			Confidence:    0.9,
		}
		issues = append(issues, issue)
	}

	// Check for var instead of let/const
	if regexp.MustCompile(`\bvar\s+`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityWarning,
			Title:         "Use let/const instead of var",
			Message:       "Prefer let or const over var for variable declarations",
			File:          filename,
			Line:          lineNumber,
			Rule:          "no-var",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Replace var with let or const",
			Confidence:    0.9,
		}
		issues = append(issues, issue)
	}

	return issues
}

// checkPython performs Python-specific checks
func (cc *CodeChecker) checkPython(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Check for print statements
	if regexp.MustCompile(`\bprint\s*\(`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityInfo,
			Title:         "Print statement found",
			Message:       "Consider using logging instead of print statements",
			File:          filename,
			Line:          lineNumber,
			Rule:          "no-print",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Use logging module instead of print",
			Confidence:    0.7,
		}
		issues = append(issues, issue)
	}

	// Check for unused imports (basic check)
	if regexp.MustCompile(`^import\s+`).MatchString(line) {
		importName := cc.extractImportName(line)
		// TODO: Implement unused import detection
		// This would need more context to properly check if used
		_ = importName // Acknowledge variable to avoid unused variable warning
	}

	return issues
}

// checkGo performs Go-specific checks
func (cc *CodeChecker) checkGo(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Check for context.TODO()
	if strings.Contains(line, "context.TODO()") {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityInfo,
			Title:         "context.TODO() usage",
			Message:       "Replace context.TODO() with proper context",
			File:          filename,
			Line:          lineNumber,
			Rule:          "no-context-todo",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Use context.Background() or pass context from caller",
			Confidence:    0.9,
		}
		issues = append(issues, issue)
	}

	// Check for panic usage
	if regexp.MustCompile(`\bpanic\s*\(`).MatchString(line) {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityWarning,
			Title:         "Panic usage detected",
			Message:       "Avoid panic, return errors instead",
			File:          filename,
			Line:          lineNumber,
			Rule:          "no-panic",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Return error instead of using panic",
			Confidence:    0.8,
		}
		issues = append(issues, issue)
	}

	return issues
}

// checkJava performs Java-specific checks
func (cc *CodeChecker) checkJava(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Check for System.out.println
	if strings.Contains(line, "System.out.println(") {
		issue := models.Issue{
			Type:          models.VibeTypeCode,
			Severity:      models.SeverityWarning,
			Title:         "System.out.println found",
			Message:       "Use proper logging instead of System.out.println",
			File:          filename,
			Line:          lineNumber,
			Rule:          "no-system-out",
			Context:       utils.TruncateString(line, 100),
			Fixable:       true,
			FixSuggestion: "Use a logging framework like SLF4J",
			Confidence:    1.0,
		}
		issues = append(issues, issue)
	}

	return issues
}

// Helper methods

func (cc *CodeChecker) isCommentedOutCode(line string) bool {
	trimmed := strings.TrimSpace(line)

	// Check for common comment patterns followed by code-like content
	commentPatterns := []string{"//", "#", "/*", "--"}

	for _, pattern := range commentPatterns {
		if strings.HasPrefix(trimmed, pattern) {
			content := strings.TrimSpace(strings.TrimPrefix(trimmed, pattern))

			// Look for code-like patterns
			codePatterns := []*regexp.Regexp{
				regexp.MustCompile(`\w+\s*=\s*\w+`),         // assignment
				regexp.MustCompile(`\w+\([^)]*\)`),          // function call with params
				regexp.MustCompile(`\w+\(.*['"].*['"].*\)`), // function call with quotes
				regexp.MustCompile(`if\s*\(`),               // if statement
				regexp.MustCompile(`for\s*\(`),              // for loop
				regexp.MustCompile(`while\s*\(`),            // while loop
				regexp.MustCompile(`return\s+`),             // return statement
				regexp.MustCompile(`print\s*\(`),            // print function
			}

			for _, pattern := range codePatterns {
				if pattern.MatchString(content) {
					return true
				}
			}
		}
	}

	return false
}

func (cc *CodeChecker) countFunctionLines(lines []string, start int) int {
	braceCount := 0
	lineCount := 0

	for i := start; i < len(lines); i++ {
		line := lines[i]
		lineCount++

		// Count braces to find function end
		braceCount += strings.Count(line, "{")
		braceCount -= strings.Count(line, "}")

		if braceCount == 0 && i > start {
			break
		}
	}

	return lineCount
}

func (cc *CodeChecker) increasesNesting(line string) bool {
	// Simple heuristic for nesting increase
	return strings.Contains(line, "{") ||
		strings.Contains(line, "if ") ||
		strings.Contains(line, "for ") ||
		strings.Contains(line, "while ") ||
		strings.Contains(line, "switch ") ||
		strings.Contains(line, "try ")
}

func (cc *CodeChecker) decreasesNesting(line string) bool {
	return strings.Contains(line, "}")
}

func (cc *CodeChecker) normalizeBlock(block string) string {
	// Remove whitespace and comments for comparison
	lines := strings.Split(block, "\n")
	var normalized []string

	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" && !strings.HasPrefix(trimmed, "//") && !strings.HasPrefix(trimmed, "#") {
			normalized = append(normalized, trimmed)
		}
	}

	return strings.Join(normalized, "\n")
}

func (cc *CodeChecker) findFunctionEnd(lines []string, start int) int {
	braceCount := 0

	for i := start; i < len(lines); i++ {
		line := lines[i]
		braceCount += strings.Count(line, "{")
		braceCount -= strings.Count(line, "}")

		if braceCount == 0 && i > start {
			return i + 1
		}
	}

	return len(lines)
}

func (cc *CodeChecker) calculateComplexity(lines []string) int {
	complexity := 1 // Base complexity

	complexityPatterns := []*regexp.Regexp{
		regexp.MustCompile(`\bif\b`),
		regexp.MustCompile(`\belse\b`),
		regexp.MustCompile(`\bfor\b`),
		regexp.MustCompile(`\bwhile\b`),
		regexp.MustCompile(`\bcase\b`),
		regexp.MustCompile(`\bcatch\b`),
		regexp.MustCompile(`\b&&\b`),
		regexp.MustCompile(`\b\|\|\b`),
		regexp.MustCompile(`\?\s*:`), // ternary operator
	}

	for _, line := range lines {
		for _, pattern := range complexityPatterns {
			matches := pattern.FindAllString(line, -1)
			complexity += len(matches)
		}
	}

	return complexity
}

func (cc *CodeChecker) isCommonNumber(s string) bool {
	commonNumbers := []string{"2", "3", "4", "5", "10", "100", "1000", "3000", "8080", "24", "60", "365"}
	for _, common := range commonNumbers {
		if s == common {
			return true
		}
	}
	return false
}

func (cc *CodeChecker) isInComment(line, number string) bool {
	// Simple check if number appears after comment markers
	commentIndex := strings.Index(line, "//")
	if commentIndex == -1 {
		commentIndex = strings.Index(line, "#")
	}
	if commentIndex == -1 {
		commentIndex = strings.Index(line, "/*")
	}

	if commentIndex != -1 {
		numberIndex := strings.Index(line, number)
		return numberIndex > commentIndex
	}

	return false
}

func (cc *CodeChecker) extractImportName(line string) string {
	// Simple extraction of import name
	parts := strings.Fields(line)
	if len(parts) >= 2 {
		return parts[1]
	}
	return ""
}

func (cc *CodeChecker) getLanguageRules(ext string) *LanguageRules {
	return cc.languageRules[ext]
}

func (cc *CodeChecker) initializeLanguageRules() {
	// JavaScript/TypeScript rules
	jsRules := &LanguageRules{
		Extensions: []string{".js", ".jsx", ".ts", ".tsx"},
		FunctionPatterns: []*regexp.Regexp{
			regexp.MustCompile(`function\s+\w+\s*\(`),
			regexp.MustCompile(`\w+\s*:\s*function\s*\(`),
			regexp.MustCompile(`\w+\s*=>\s*{`),
			regexp.MustCompile(`\w+\s*=\s*function\s*\(`),
		},
		ClassPatterns: []*regexp.Regexp{
			regexp.MustCompile(`class\s+\w+`),
		},
	}
	cc.languageRules[".js"] = jsRules
	cc.languageRules[".jsx"] = jsRules
	cc.languageRules[".ts"] = jsRules
	cc.languageRules[".tsx"] = jsRules

	// Python rules
	pyRules := &LanguageRules{
		Extensions: []string{".py"},
		FunctionPatterns: []*regexp.Regexp{
			regexp.MustCompile(`def\s+\w+\s*\(`),
		},
		ClassPatterns: []*regexp.Regexp{
			regexp.MustCompile(`class\s+\w+`),
		},
	}
	cc.languageRules[".py"] = pyRules

	// Go rules
	goRules := &LanguageRules{
		Extensions: []string{".go"},
		FunctionPatterns: []*regexp.Regexp{
			regexp.MustCompile(`func\s+\w+\s*\(`),
			regexp.MustCompile(`func\s*\(\w*\s*\*?\w+\)\s*\w+\s*\(`),
		},
	}
	cc.languageRules[".go"] = goRules

	// Java rules
	javaRules := &LanguageRules{
		Extensions: []string{".java"},
		FunctionPatterns: []*regexp.Regexp{
			regexp.MustCompile(`(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\(`),
		},
		ClassPatterns: []*regexp.Regexp{
			regexp.MustCompile(`(public|private)?\s*class\s+\w+`),
		},
	}
	cc.languageRules[".java"] = javaRules
}
