package fix

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"kodevibe/internal/models"

	"github.com/sirupsen/logrus"
)

// Fixer handles automatic fixing of detected issues
type Fixer struct {
	config *models.Configuration
	logger *logrus.Logger
	fixers map[string]FixRule
}

// FixRule defines how to fix a specific rule violation
type FixRule struct {
	Name        string
	Pattern     *regexp.Regexp
	Replacement string
	FileTypes   []string
	Confidence  float64
	Validator   func(original, fixed string) bool
}

// NewFixer creates a new fixer instance
func NewFixer(config *models.Configuration, logger *logrus.Logger) *Fixer {
	fixer := &Fixer{
		config: config,
		logger: logger,
		fixers: make(map[string]FixRule),
	}

	fixer.initializeFixRules()
	return fixer
}

// Fix attempts to automatically fix issues in the specified paths
func (f *Fixer) Fix(paths []string, autoFix bool, createBackup bool, rules []string) error {
	f.logger.Info("Starting auto-fix operation")

	var totalFixed int
	var totalErrors int

	for _, path := range paths {
		err := filepath.Walk(path, func(filePath string, info os.FileInfo, err error) error {
			if err != nil {
				return err
			}

			if info.IsDir() {
				return nil
			}

			if f.shouldSkipFile(filePath) {
				return nil
			}

			fixed, errors := f.fixFile(filePath, autoFix, createBackup, rules)
			totalFixed += fixed
			totalErrors += errors

			return nil
		})

		if err != nil {
			f.logger.Errorf("Error walking path %s: %v", path, err)
		}
	}

	f.logger.Infof("Auto-fix completed: %d fixes applied, %d errors", totalFixed, totalErrors)
	return nil
}

// fixFile fixes issues in a single file
func (f *Fixer) fixFile(filePath string, autoFix bool, createBackup bool, rules []string) (int, int) {
	var fixedCount int
	var errorCount int

	content, err := os.ReadFile(filePath)
	if err != nil {
		f.logger.Errorf("Failed to read file %s: %v", filePath, err)
		return 0, 1
	}

	originalContent := string(content)
	modifiedContent := originalContent
	fileModified := false

	ext := strings.ToLower(filepath.Ext(filePath))

	// Apply fix rules
	for ruleName, fixRule := range f.fixers {
		// Skip if specific rules were requested and this isn't one of them
		if len(rules) > 0 && !contains(rules, ruleName) {
			continue
		}

		// Check if rule applies to this file type
		if !f.appliesToFileType(fixRule, ext) {
			continue
		}

		// Apply the fix
		newContent := fixRule.Pattern.ReplaceAllString(modifiedContent, fixRule.Replacement)
		if newContent != modifiedContent {
			if autoFix || f.confirmFix(filePath, ruleName, modifiedContent, newContent) {
				// Validate the fix if validator exists
				if fixRule.Validator != nil && !fixRule.Validator(modifiedContent, newContent) {
					f.logger.Warnf("Fix validation failed for rule %s in file %s", ruleName, filePath)
					errorCount++
					continue
				}

				modifiedContent = newContent
				fileModified = true
				fixedCount++
				f.logger.Infof("Applied fix %s to %s", ruleName, filePath)
			}
		}
	}

	// Write the file if it was modified
	if fileModified {
		// Create backup if requested
		if createBackup {
			backupPath := filePath + ".backup." + time.Now().Format("20060102-150405")
			if err := os.WriteFile(backupPath, []byte(originalContent), 0644); err != nil {
				f.logger.Errorf("Failed to create backup %s: %v", backupPath, err)
				errorCount++
			} else {
				f.logger.Infof("Created backup: %s", backupPath)
			}
		}

		// Write the modified content
		if err := os.WriteFile(filePath, []byte(modifiedContent), 0644); err != nil {
			f.logger.Errorf("Failed to write fixed file %s: %v", filePath, err)
			errorCount++
		}
	}

	return fixedCount, errorCount
}

// shouldSkipFile determines if a file should be skipped
func (f *Fixer) shouldSkipFile(filePath string) bool {
	// Check exclude patterns
	for _, pattern := range f.config.Exclude.Files {
		if matched, err := filepath.Match(pattern, filePath); err == nil && matched {
			return true
		}
	}

	// Skip binary files
	if f.isBinaryFile(filePath) {
		return true
	}

	return false
}

// isBinaryFile checks if a file is binary
func (f *Fixer) isBinaryFile(filePath string) bool {
	file, err := os.Open(filePath)
	if err != nil {
		return true
	}
	defer file.Close()

	// Read first 512 bytes to check for binary content
	buffer := make([]byte, 512)
	n, err := file.Read(buffer)
	if err != nil {
		return true
	}

	// Check for null bytes (common in binary files)
	for i := 0; i < n; i++ {
		if buffer[i] == 0 {
			return true
		}
	}

	return false
}

// appliesToFileType checks if a fix rule applies to the given file type
func (f *Fixer) appliesToFileType(rule FixRule, ext string) bool {
	if len(rule.FileTypes) == 0 {
		return true // Apply to all file types if none specified
	}

	for _, fileType := range rule.FileTypes {
		if fileType == ext {
			return true
		}
	}

	return false
}

// confirmFix asks user for confirmation before applying a fix
func (f *Fixer) confirmFix(filePath, ruleName, original, fixed string) bool {
	fmt.Printf("\n🔧 Found fixable issue in %s\n", filePath)
	fmt.Printf("Rule: %s\n", ruleName)
	fmt.Printf("Apply fix? (y/n): ")

	reader := bufio.NewReader(os.Stdin)
	response, err := reader.ReadString('\n')
	if err != nil {
		return false
	}

	response = strings.TrimSpace(strings.ToLower(response))
	return response == "y" || response == "yes"
}

// initializeFixRules initializes the built-in fix rules
func (f *Fixer) initializeFixRules() {
	// JavaScript/TypeScript fixes
	f.fixers["no-console-log"] = FixRule{
		Name:        "Remove console.log statements",
		Pattern:     regexp.MustCompile(`console\.log\([^)]*\);\s*`),
		Replacement: "",
		FileTypes:   []string{".js", ".jsx", ".ts", ".tsx"},
		Confidence:  0.9,
	}

	f.fixers["strict-equality"] = FixRule{
		Name:        "Use strict equality",
		Pattern:     regexp.MustCompile(`([^!=])==[^=]`),
		Replacement: "${1}===",
		FileTypes:   []string{".js", ".jsx", ".ts", ".tsx"},
		Confidence:  0.95,
	}

	f.fixers["var-to-let"] = FixRule{
		Name:        "Replace var with let",
		Pattern:     regexp.MustCompile(`\bvar\b`),
		Replacement: "let",
		FileTypes:   []string{".js", ".jsx", ".ts", ".tsx"},
		Confidence:  0.8,
	}

	// Python fixes
	f.fixers["remove-print"] = FixRule{
		Name:        "Remove print statements",
		Pattern:     regexp.MustCompile(`print\([^)]*\)\s*`),
		Replacement: "",
		FileTypes:   []string{".py"},
		Confidence:  0.7, // Lower confidence as prints might be intentional
	}

	// Go fixes
	f.fixers["context-todo"] = FixRule{
		Name:        "Replace context.TODO",
		Pattern:     regexp.MustCompile(`context\.TODO\(\)`),
		Replacement: "context.Background()",
		FileTypes:   []string{".go"},
		Confidence:  0.8,
	}

	// Generic fixes
	f.fixers["trailing-whitespace"] = FixRule{
		Name:        "Remove trailing whitespace",
		Pattern:     regexp.MustCompile(`[ \t]+$`),
		Replacement: "",
		Confidence:  1.0,
	}

	f.fixers["multiple-blank-lines"] = FixRule{
		Name:        "Remove multiple blank lines",
		Pattern:     regexp.MustCompile(`\n\n\n+`),
		Replacement: "\n\n",
		Confidence:  0.9,
	}

	f.fixers["missing-final-newline"] = FixRule{
		Name:        "Add final newline",
		Pattern:     regexp.MustCompile(`[^\n]$`),
		Replacement: "$0\n",
		Confidence:  0.9,
		Validator: func(original, fixed string) bool {
			// Only add newline if file is not empty
			return len(strings.TrimSpace(original)) > 0
		},
	}

	// Security fixes (conservative)
	f.fixers["hardcoded-credentials"] = FixRule{
		Name:        "Comment out hardcoded credentials",
		Pattern:     regexp.MustCompile(`(password|secret|key)\s*=\s*['"][^'"]{8,}['"]`),
		Replacement: "// TODO: Move to environment variable - $0",
		Confidence:  0.6, // Lower confidence, requires manual review
	}
}

// GetAvailableFixRules returns a list of available fix rules
func (f *Fixer) GetAvailableFixRules() []string {
	var rules []string
	for ruleName := range f.fixers {
		rules = append(rules, ruleName)
	}
	return rules
}

// ValidateFix validates that a fix doesn't break the code
func (f *Fixer) ValidateFix(original, fixed, filePath string) error {
	// Basic validation - check that file is still valid syntax
	ext := strings.ToLower(filepath.Ext(filePath))

	switch ext {
	case ".js", ".jsx", ".ts", ".tsx":
		return f.validateJavaScript(fixed)
	case ".py":
		return f.validatePython(fixed)
	case ".go":
		return f.validateGo(fixed)
	}

	return nil
}

// validateJavaScript performs basic JavaScript syntax validation
func (f *Fixer) validateJavaScript(content string) error {
	// Basic checks for common syntax errors
	braceCount := strings.Count(content, "{") - strings.Count(content, "}")
	if braceCount != 0 {
		return fmt.Errorf("unbalanced braces")
	}

	parenCount := strings.Count(content, "(") - strings.Count(content, ")")
	if parenCount != 0 {
		return fmt.Errorf("unbalanced parentheses")
	}

	return nil
}

// validatePython performs basic Python syntax validation
func (f *Fixer) validatePython(content string) error {
	// Check for basic indentation issues
	lines := strings.Split(content, "\n")
	for i, line := range lines {
		if strings.HasSuffix(strings.TrimSpace(line), ":") {
			// Line ends with colon, next line should be indented
			if i+1 < len(lines) {
				nextLine := lines[i+1]
				if strings.TrimSpace(nextLine) != "" && !strings.HasPrefix(nextLine, " ") && !strings.HasPrefix(nextLine, "\t") {
					return fmt.Errorf("indentation error at line %d", i+2)
				}
			}
		}
	}

	return nil
}

// validateGo performs basic Go syntax validation
func (f *Fixer) validateGo(content string) error {
	// Basic checks for Go syntax
	braceCount := strings.Count(content, "{") - strings.Count(content, "}")
	if braceCount != 0 {
		return fmt.Errorf("unbalanced braces")
	}

	return nil
}

// Helper function
func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}
