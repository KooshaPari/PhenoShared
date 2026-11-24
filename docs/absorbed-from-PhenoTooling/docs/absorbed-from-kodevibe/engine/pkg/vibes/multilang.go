package vibes

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"kodevibe/internal/models"
)

// MultiLanguageChecker provides enhanced language-specific analysis
type MultiLanguageChecker struct {
	supportedLanguages map[string]*LanguageConfig
}

// LanguageConfig contains language-specific analysis rules
type LanguageConfig struct {
	Name            string
	Extensions      []string
	CommentStyles   []CommentStyle
	Keywords        []string
	SecurityRules   []SecurityRule
	QualityRules    []QualityRule
	ComplexityRules []ComplexityRule
}

// CommentStyle defines how comments are written in a language
type CommentStyle struct {
	Single string // e.g., "//" for Go, "#" for Python
	Multi  struct {
		Start string // e.g., "/*"
		End   string // e.g., "*/"
	}
}

// SecurityRule defines language-specific security patterns
type SecurityRule struct {
	Pattern     *regexp.Regexp
	Description string
	Severity    string
	Category    string
	Fix         string
}

// QualityRule defines code quality patterns
type QualityRule struct {
	Pattern     *regexp.Regexp
	Description string
	Severity    string
	Category    string
	Fix         string
}

// ComplexityRule defines complexity measurement patterns
type ComplexityRule struct {
	Pattern     *regexp.Regexp
	Description string
	Weight      int
}

// NewMultiLanguageChecker creates a new multi-language analysis checker
func NewMultiLanguageChecker() *MultiLanguageChecker {
	checker := &MultiLanguageChecker{
		supportedLanguages: make(map[string]*LanguageConfig),
	}

	checker.initializeLanguageConfigs()
	return checker
}

// CheckFile analyzes a file with language-specific rules
func (m *MultiLanguageChecker) CheckFile(filePath string) ([]models.Issue, error) {
	language := m.detectLanguage(filePath)
	if language == nil {
		return nil, fmt.Errorf("unsupported language for file: %s", filePath)
	}

	content, err := os.ReadFile(filePath)
	if err != nil {
		return nil, fmt.Errorf("failed to read file: %w", err)
	}

	var issues []models.Issue

	// Apply security rules
	securityIssues := m.checkSecurityRules(string(content), filePath, language)
	issues = append(issues, securityIssues...)

	// Apply quality rules
	qualityIssues := m.checkQualityRules(string(content), filePath, language)
	issues = append(issues, qualityIssues...)

	// Check complexity
	complexityIssues := m.checkComplexity(string(content), filePath, language)
	issues = append(issues, complexityIssues...)

	return issues, nil
}

// detectLanguage determines the programming language based on file extension
func (m *MultiLanguageChecker) detectLanguage(filePath string) *LanguageConfig {
	ext := strings.ToLower(filepath.Ext(filePath))

	for _, config := range m.supportedLanguages {
		for _, supportedExt := range config.Extensions {
			if ext == supportedExt {
				return config
			}
		}
	}

	return nil
}

// checkSecurityRules applies security rules for the detected language
func (m *MultiLanguageChecker) checkSecurityRules(content, filePath string, lang *LanguageConfig) []models.Issue {
	var issues []models.Issue
	lines := strings.Split(content, "\n")

	for _, rule := range lang.SecurityRules {
		for lineNum, line := range lines {
			if rule.Pattern.MatchString(line) {
				issues = append(issues, models.Issue{
					File:     filePath,
					Line:     lineNum + 1,
					Column:   1,
					Severity: models.SeverityLevel(rule.Severity),
					Message:  rule.Description,
					Category: rule.Category,
					Fix:      rule.Fix,
				})
			}
		}
	}

	return issues
}

// checkQualityRules applies code quality rules
func (m *MultiLanguageChecker) checkQualityRules(content, filePath string, lang *LanguageConfig) []models.Issue {
	var issues []models.Issue
	lines := strings.Split(content, "\n")

	for _, rule := range lang.QualityRules {
		for lineNum, line := range lines {
			if rule.Pattern.MatchString(line) {
				issues = append(issues, models.Issue{
					File:     filePath,
					Line:     lineNum + 1,
					Column:   1,
					Severity: models.SeverityLevel(rule.Severity),
					Message:  rule.Description,
					Category: rule.Category,
					Fix:      rule.Fix,
				})
			}
		}
	}

	return issues
}

// checkComplexity measures code complexity
func (m *MultiLanguageChecker) checkComplexity(content, filePath string, lang *LanguageConfig) []models.Issue {
	var issues []models.Issue
	scanner := bufio.NewScanner(strings.NewReader(content))
	lineNum := 0
	complexity := 0

	for scanner.Scan() {
		lineNum++
		line := scanner.Text()

		for _, rule := range lang.ComplexityRules {
			if rule.Pattern.MatchString(line) {
				complexity += rule.Weight
			}
		}

		// Check if complexity threshold is exceeded
		if complexity > 10 { // Configurable threshold
			issues = append(issues, models.Issue{
				File:     filePath,
				Line:     lineNum,
				Column:   1,
				Severity: models.SeverityWarning,
				Message:  fmt.Sprintf("High complexity detected (score: %d)", complexity),
				Category: "complexity",
				Fix:      "Consider breaking this code into smaller functions",
			})
			complexity = 0 // Reset for next section
		}
	}

	return issues
}

// initializeLanguageConfigs sets up language-specific configurations
func (m *MultiLanguageChecker) initializeLanguageConfigs() {
	m.supportedLanguages["go"] = m.createGoConfig()
	m.supportedLanguages["javascript"] = m.createJavaScriptConfig()
	m.supportedLanguages["typescript"] = m.createTypeScriptConfig()
	m.supportedLanguages["python"] = m.createPythonConfig()
	m.supportedLanguages["java"] = m.createJavaConfig()
	m.supportedLanguages["rust"] = m.createRustConfig()
	m.supportedLanguages["csharp"] = m.createCSharpConfig()
	m.supportedLanguages["cpp"] = m.createCppConfig()
	m.supportedLanguages["php"] = m.createPhpConfig()
	m.supportedLanguages["ruby"] = m.createRubyConfig()
}

// createGoConfig creates Go language configuration
func (m *MultiLanguageChecker) createGoConfig() *LanguageConfig {
	return &LanguageConfig{
		Name:       "Go",
		Extensions: []string{".go"},
		CommentStyles: []CommentStyle{
			{Single: "//", Multi: struct{ Start, End string }{Start: "/*", End: "*/"}},
		},
		Keywords: []string{"package", "import", "func", "var", "const", "type", "struct", "interface"},
		SecurityRules: []SecurityRule{
			{
				Pattern:     regexp.MustCompile(`sql\.Query\([^$]`),
				Description: "Potential SQL injection vulnerability - use parameterized queries",
				Severity:    "high",
				Category:    "security",
				Fix:         "Use sql.Query with parameters: db.Query(\"SELECT * FROM users WHERE id = ?\", userID)",
			},
			{
				Pattern:     regexp.MustCompile(`fmt\.Sprintf.*%[sv].*\+`),
				Description: "String concatenation in format string may lead to injection",
				Severity:    "medium",
				Category:    "security",
				Fix:         "Use proper parameterization instead of string concatenation",
			},
			{
				Pattern:     regexp.MustCompile(`crypto/md5|crypto/sha1`),
				Description: "Weak cryptographic hash function",
				Severity:    "medium",
				Category:    "security",
				Fix:         "Use crypto/sha256 or stronger hash functions",
			},
		},
		QualityRules: []QualityRule{
			{
				Pattern:     regexp.MustCompile(`^[[:space:]]*if.*{[[:space:]]*$`),
				Description: "Consider using early return to reduce nesting",
				Severity:    "low",
				Category:    "readability",
				Fix:         "Use early return: if condition { return }",
			},
			{
				Pattern:     regexp.MustCompile(`func.*\([^)]{50,}`),
				Description: "Function has too many parameters",
				Severity:    "medium",
				Category:    "maintainability",
				Fix:         "Consider using a struct to group related parameters",
			},
		},
		ComplexityRules: []ComplexityRule{
			{Pattern: regexp.MustCompile(`\bif\b|\bfor\b|\bswitch\b|\bselect\b`), Description: "Control flow", Weight: 1},
			{Pattern: regexp.MustCompile(`\bfunc\b`), Description: "Function definition", Weight: 1},
			{Pattern: regexp.MustCompile(`\bgo\b\s+\w+\(`), Description: "Goroutine", Weight: 2},
		},
	}
}

// createJavaScriptConfig creates JavaScript language configuration
func (m *MultiLanguageChecker) createJavaScriptConfig() *LanguageConfig {
	return &LanguageConfig{
		Name:       "JavaScript",
		Extensions: []string{".js", ".jsx", ".mjs"},
		CommentStyles: []CommentStyle{
			{Single: "//", Multi: struct{ Start, End string }{Start: "/*", End: "*/"}},
		},
		Keywords: []string{"function", "var", "let", "const", "class", "import", "export"},
		SecurityRules: []SecurityRule{
			{
				Pattern:     regexp.MustCompile(`eval\(|Function\(|setTimeout\(.*string|setInterval\(.*string`),
				Description: "Dangerous use of eval or code execution functions",
				Severity:    "high",
				Category:    "security",
				Fix:         "Avoid eval() and use safer alternatives like JSON.parse()",
			},
			{
				Pattern:     regexp.MustCompile(`innerHTML\s*=\s*.*\+`),
				Description: "Potential XSS vulnerability with innerHTML",
				Severity:    "high",
				Category:    "security",
				Fix:         "Use textContent or properly sanitize HTML content",
			},
			{
				Pattern:     regexp.MustCompile(`document\.write\(`),
				Description: "document.write can lead to XSS vulnerabilities",
				Severity:    "medium",
				Category:    "security",
				Fix:         "Use modern DOM manipulation methods",
			},
		},
		QualityRules: []QualityRule{
			{
				Pattern:     regexp.MustCompile(`==\s|!=\s`),
				Description: "Use strict equality operators (=== and !==)",
				Severity:    "low",
				Category:    "best-practices",
				Fix:         "Replace == with === and != with !==",
			},
			{
				Pattern:     regexp.MustCompile(`var\s+\w+`),
				Description: "Prefer const or let over var",
				Severity:    "low",
				Category:    "best-practices",
				Fix:         "Use 'const' for constants or 'let' for variables",
			},
		},
		ComplexityRules: []ComplexityRule{
			{Pattern: regexp.MustCompile(`\bif\b|\bfor\b|\bwhile\b|\bswitch\b`), Description: "Control flow", Weight: 1},
			{Pattern: regexp.MustCompile(`\bfunction\b|\=\>`), Description: "Function definition", Weight: 1},
			{Pattern: regexp.MustCompile(`\btry\b|\bcatch\b`), Description: "Exception handling", Weight: 1},
		},
	}
}

// createTypeScriptConfig creates TypeScript language configuration
func (m *MultiLanguageChecker) createTypeScriptConfig() *LanguageConfig {
	config := m.createJavaScriptConfig()
	config.Name = "TypeScript"
	config.Extensions = []string{".ts", ".tsx"}

	// Add TypeScript-specific rules
	config.QualityRules = append(config.QualityRules, QualityRule{
		Pattern:     regexp.MustCompile(`:\s*any\b`),
		Description: "Avoid using 'any' type, use specific types instead",
		Severity:    "medium",
		Category:    "type-safety",
		Fix:         "Define specific types or interfaces",
	})

	return config
}

// createPythonConfig creates Python language configuration
func (m *MultiLanguageChecker) createPythonConfig() *LanguageConfig {
	return &LanguageConfig{
		Name:       "Python",
		Extensions: []string{".py", ".pyw"},
		CommentStyles: []CommentStyle{
			{Single: "#", Multi: struct{ Start, End string }{Start: "\"\"\"", End: "\"\"\""}},
		},
		Keywords: []string{"def", "class", "import", "from", "if", "else", "for", "while", "try", "except"},
		SecurityRules: []SecurityRule{
			{
				Pattern:     regexp.MustCompile(`eval\(|exec\(|compile\(`),
				Description: "Dangerous use of eval, exec, or compile functions",
				Severity:    "high",
				Category:    "security",
				Fix:         "Use safer alternatives like ast.literal_eval() for data parsing",
			},
			{
				Pattern:     regexp.MustCompile(`subprocess\.(call|run|Popen).*shell=True`),
				Description: "Command injection vulnerability with shell=True",
				Severity:    "high",
				Category:    "security",
				Fix:         "Use shell=False and pass arguments as a list",
			},
			{
				Pattern:     regexp.MustCompile(`os\.system\(|commands\.|popen\(`),
				Description: "Potential command injection vulnerability",
				Severity:    "medium",
				Category:    "security",
				Fix:         "Use subprocess module with proper argument handling",
			},
		},
		QualityRules: []QualityRule{
			{
				Pattern:     regexp.MustCompile(`except:\s*$`),
				Description: "Bare except clause catches all exceptions",
				Severity:    "medium",
				Category:    "error-handling",
				Fix:         "Catch specific exceptions: except SpecificError:",
			},
			{
				Pattern:     regexp.MustCompile(`print\(`),
				Description: "Consider using logging instead of print statements",
				Severity:    "low",
				Category:    "best-practices",
				Fix:         "Use logging.info() or appropriate log level",
			},
		},
		ComplexityRules: []ComplexityRule{
			{Pattern: regexp.MustCompile(`\bif\b|\bfor\b|\bwhile\b|\belif\b`), Description: "Control flow", Weight: 1},
			{Pattern: regexp.MustCompile(`\bdef\b|\bclass\b`), Description: "Function/class definition", Weight: 1},
			{Pattern: regexp.MustCompile(`\btry\b|\bexcept\b`), Description: "Exception handling", Weight: 1},
		},
	}
}

// createJavaConfig creates Java language configuration
func (m *MultiLanguageChecker) createJavaConfig() *LanguageConfig {
	return &LanguageConfig{
		Name:       "Java",
		Extensions: []string{".java"},
		CommentStyles: []CommentStyle{
			{Single: "//", Multi: struct{ Start, End string }{Start: "/*", End: "*/"}},
		},
		Keywords: []string{"public", "private", "protected", "class", "interface", "extends", "implements"},
		SecurityRules: []SecurityRule{
			{
				Pattern:     regexp.MustCompile(`Runtime\.getRuntime\(\)\.exec\(`),
				Description: "Command injection vulnerability with Runtime.exec()",
				Severity:    "high",
				Category:    "security",
				Fix:         "Use ProcessBuilder with proper argument validation",
			},
			{
				Pattern:     regexp.MustCompile(`Statement\.execute\(.*\+.*\)`),
				Description: "Potential SQL injection with string concatenation",
				Severity:    "high",
				Category:    "security",
				Fix:         "Use PreparedStatement with parameters",
			},
		},
		QualityRules: []QualityRule{
			{
				Pattern:     regexp.MustCompile(`catch\s*\([^)]*Exception[^)]*\)\s*\{\s*\}`),
				Description: "Empty catch block suppresses exceptions",
				Severity:    "medium",
				Category:    "error-handling",
				Fix:         "Handle exceptions appropriately or log them",
			},
		},
		ComplexityRules: []ComplexityRule{
			{Pattern: regexp.MustCompile(`\bif\b|\bfor\b|\bwhile\b|\bswitch\b`), Description: "Control flow", Weight: 1},
			{Pattern: regexp.MustCompile(`\bpublic\b|\bprivate\b|\bprotected\b.*\(`), Description: "Method definition", Weight: 1},
		},
	}
}

// createRustConfig creates Rust language configuration
func (m *MultiLanguageChecker) createRustConfig() *LanguageConfig {
	return &LanguageConfig{
		Name:       "Rust",
		Extensions: []string{".rs"},
		CommentStyles: []CommentStyle{
			{Single: "//", Multi: struct{ Start, End string }{Start: "/*", End: "*/"}},
		},
		Keywords: []string{"fn", "struct", "enum", "impl", "trait", "use", "mod", "pub"},
		SecurityRules: []SecurityRule{
			{
				Pattern:     regexp.MustCompile(`unsafe\s*\{`),
				Description: "Unsafe block detected - ensure memory safety",
				Severity:    "medium",
				Category:    "security",
				Fix:         "Minimize unsafe code and document safety invariants",
			},
		},
		QualityRules: []QualityRule{
			{
				Pattern:     regexp.MustCompile(`unwrap\(\)`),
				Description: "Consider using proper error handling instead of unwrap()",
				Severity:    "low",
				Category:    "error-handling",
				Fix:         "Use match, if let, or ? operator for error handling",
			},
			{
				Pattern:     regexp.MustCompile(`clone\(\).*clone\(\)`),
				Description: "Multiple clones detected - consider borrowing",
				Severity:    "low",
				Category:    "performance",
				Fix:         "Use references (&) instead of cloning when possible",
			},
		},
		ComplexityRules: []ComplexityRule{
			{Pattern: regexp.MustCompile(`\bif\b|\bfor\b|\bwhile\b|\bmatch\b`), Description: "Control flow", Weight: 1},
			{Pattern: regexp.MustCompile(`\bfn\b`), Description: "Function definition", Weight: 1},
		},
	}
}

// Additional language configs...
func (m *MultiLanguageChecker) createCSharpConfig() *LanguageConfig {
	return &LanguageConfig{
		Name:       "C#",
		Extensions: []string{".cs"},
		CommentStyles: []CommentStyle{
			{Single: "//", Multi: struct{ Start, End string }{Start: "/*", End: "*/"}},
		},
		SecurityRules: []SecurityRule{
			{
				Pattern:     regexp.MustCompile(`SqlCommand.*CommandText.*\+`),
				Description: "Potential SQL injection with string concatenation",
				Severity:    "high",
				Category:    "security",
				Fix:         "Use parameterized queries with SqlParameter",
			},
		},
		QualityRules: []QualityRule{
			{
				Pattern:     regexp.MustCompile(`catch\s*\([^)]*\)\s*\{\s*\}`),
				Description: "Empty catch block suppresses exceptions",
				Severity:    "medium",
				Category:    "error-handling",
				Fix:         "Handle exceptions appropriately",
			},
		},
		ComplexityRules: []ComplexityRule{
			{Pattern: regexp.MustCompile(`\bif\b|\bfor\b|\bwhile\b|\bswitch\b`), Description: "Control flow", Weight: 1},
		},
	}
}

func (m *MultiLanguageChecker) createCppConfig() *LanguageConfig {
	return &LanguageConfig{
		Name:       "C++",
		Extensions: []string{".cpp", ".cc", ".cxx", ".c++", ".h", ".hpp"},
		CommentStyles: []CommentStyle{
			{Single: "//", Multi: struct{ Start, End string }{Start: "/*", End: "*/"}},
		},
		SecurityRules: []SecurityRule{
			{
				Pattern:     regexp.MustCompile(`strcpy\(|strcat\(|sprintf\(`),
				Description: "Buffer overflow vulnerability with unsafe string functions",
				Severity:    "high",
				Category:    "security",
				Fix:         "Use safe alternatives like strncpy, strncat, snprintf",
			},
		},
		ComplexityRules: []ComplexityRule{
			{Pattern: regexp.MustCompile(`\bif\b|\bfor\b|\bwhile\b|\bswitch\b`), Description: "Control flow", Weight: 1},
		},
	}
}

func (m *MultiLanguageChecker) createPhpConfig() *LanguageConfig {
	return &LanguageConfig{
		Name:       "PHP",
		Extensions: []string{".php", ".phtml"},
		CommentStyles: []CommentStyle{
			{Single: "//", Multi: struct{ Start, End string }{Start: "/*", End: "*/"}},
		},
		SecurityRules: []SecurityRule{
			{
				Pattern:     regexp.MustCompile(`eval\(|\$\{.*\}`),
				Description: "Code injection vulnerability with eval or variable variables",
				Severity:    "high",
				Category:    "security",
				Fix:         "Avoid eval() and validate all user inputs",
			},
		},
		ComplexityRules: []ComplexityRule{
			{Pattern: regexp.MustCompile(`\bif\b|\bfor\b|\bwhile\b|\bswitch\b`), Description: "Control flow", Weight: 1},
		},
	}
}

func (m *MultiLanguageChecker) createRubyConfig() *LanguageConfig {
	return &LanguageConfig{
		Name:       "Ruby",
		Extensions: []string{".rb"},
		CommentStyles: []CommentStyle{
			{Single: "#"},
		},
		SecurityRules: []SecurityRule{
			{
				Pattern:     regexp.MustCompile(`eval\(|instance_eval|class_eval`),
				Description: "Code injection vulnerability with eval methods",
				Severity:    "high",
				Category:    "security",
				Fix:         "Use safer alternatives and validate inputs",
			},
		},
		ComplexityRules: []ComplexityRule{
			{Pattern: regexp.MustCompile(`\bif\b|\bfor\b|\bwhile\b|\bcase\b`), Description: "Control flow", Weight: 1},
		},
	}
}

// GetSupportedLanguages returns a list of supported programming languages
func (m *MultiLanguageChecker) GetSupportedLanguages() []string {
	var languages []string
	for name := range m.supportedLanguages {
		languages = append(languages, name)
	}
	return languages
}
