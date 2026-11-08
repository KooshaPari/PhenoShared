package vibes

import (
	"bufio"
	"context"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"kodevibe/internal/models"
	"kodevibe/internal/utils"
)

// SecurityChecker implements security-related checks
type SecurityChecker struct {
	config           models.VibeConfig
	secretPatterns   []*SecretPattern
	vulnerabilityDB  *VulnerabilityDB
	entropyThreshold float64
	testContent      map[string]string // For testing purposes
}

// SecretPattern represents a pattern for detecting secrets
type SecretPattern struct {
	Name        string
	Pattern     *regexp.Regexp
	Confidence  float64
	Description string
	Examples    []string
}

// VulnerabilityDB represents a vulnerability database
type VulnerabilityDB struct {
	patterns map[string]*regexp.Regexp
}

// NewSecurityChecker creates a new security checker
func NewSecurityChecker() *SecurityChecker {
	checker := &SecurityChecker{
		entropyThreshold: 4.5,
		vulnerabilityDB:  NewVulnerabilityDB(),
		testContent:      make(map[string]string),
	}

	checker.initializeSecretPatterns()
	return checker
}

// Name returns the checker name
func (sc *SecurityChecker) Name() string {
	return "SecurityVibe"
}

// Type returns the vibe type
func (sc *SecurityChecker) Type() models.VibeType {
	return models.VibeTypeSecurity
}

// Configure configures the security checker
func (sc *SecurityChecker) Configure(config models.VibeConfig) error {
	sc.config = config

	// Configure entropy threshold
	if threshold, exists := config.Settings["entropy_threshold"]; exists {
		if thresholdFloat, ok := threshold.(float64); ok {
			sc.entropyThreshold = thresholdFloat
		}
	}

	return nil
}

// Supports returns true if the checker supports the given file
func (sc *SecurityChecker) Supports(filename string) bool {
	// Security checks apply to all text files
	ext := strings.ToLower(filepath.Ext(filename))
	textExtensions := []string{
		".js", ".jsx", ".ts", ".tsx", ".py", ".go", ".java", ".c", ".cpp", ".h", ".hpp",
		".rb", ".php", ".sh", ".bash", ".zsh", ".ps1", ".yaml", ".yml", ".json", ".xml",
		".html", ".htm", ".css", ".scss", ".less", ".md", ".txt", ".env", ".config",
		".properties", ".ini", ".conf", ".toml", ".sql", ".dockerfile", ".makefile",
	}

	for _, textExt := range textExtensions {
		if ext == textExt {
			return true
		}
	}

	// Also check files without extensions
	return ext == ""
}

// Check performs security checks on the provided files
func (sc *SecurityChecker) Check(ctx context.Context, files []string) ([]models.Issue, error) {
	var issues []models.Issue

	for _, file := range files {
		if !sc.Supports(file) {
			continue
		}

		fileIssues, err := sc.checkFile(file)
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

// checkFile performs security checks on a single file
func (sc *SecurityChecker) checkFile(filename string) ([]models.Issue, error) {
	var issues []models.Issue
	var lines []string

	// Check if we have test content for this file
	if sc.testContent != nil && sc.testContent[filename] != "" {
		lines = strings.Split(sc.testContent[filename], "\n")
	} else {
		file, err := os.Open(filename)
		if err != nil {
			return nil, fmt.Errorf("failed to open file: %w", err)
		}
		defer file.Close()

		scanner := bufio.NewScanner(file)
		for scanner.Scan() {
			lines = append(lines, scanner.Text())
		}

		if err := scanner.Err(); err != nil {
			return nil, fmt.Errorf("error reading file: %w", err)
		}
	}

	for lineNumber, line := range lines {
		lineNumber++ // Make it 1-based

		// Check for secrets
		secretIssues := sc.checkLineForSecrets(filename, line, lineNumber)
		issues = append(issues, secretIssues...)

		// Check for vulnerabilities
		vulnIssues := sc.checkLineForVulnerabilities(filename, line, lineNumber)
		issues = append(issues, vulnIssues...)

		// Check for hardcoded credentials
		credIssues := sc.checkLineForHardcodedCredentials(filename, line, lineNumber)
		issues = append(issues, credIssues...)

		// Check for high entropy strings
		entropyIssues := sc.checkLineForHighEntropy(filename, line, lineNumber)
		issues = append(issues, entropyIssues...)
	}

	return issues, nil
}

// checkLineForSecrets checks a line for known secret patterns
func (sc *SecurityChecker) checkLineForSecrets(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	for _, pattern := range sc.secretPatterns {
		matches := pattern.Pattern.FindAllStringSubmatch(line, -1)
		for _, match := range matches {
			if len(match) > 0 {
				// Check if this is a false positive
				if sc.isFalsePositive(filename, line, pattern.Name) {
					continue
				}

				issue := models.Issue{
					Type:       models.VibeTypeSecurity,
					Severity:   models.SeverityError,
					Title:      fmt.Sprintf("Potential %s detected", pattern.Name),
					Message:    fmt.Sprintf("Found potential %s: %s", pattern.Name, pattern.Description),
					File:       filename,
					Line:       lineNumber,
					Rule:       fmt.Sprintf("secret-detection-%s", strings.ToLower(strings.ReplaceAll(pattern.Name, " ", "-"))),
					Pattern:    pattern.Pattern.String(),
					Context:    utils.TruncateString(line, 100),
					Fixable:    false,
					Confidence: pattern.Confidence,
					Metadata: map[string]interface{}{
						"secret_type": pattern.Name,
						"match":       match[0],
					},
				}

				issues = append(issues, issue)
			}
		}
	}

	return issues
}

// checkLineForVulnerabilities checks a line for security vulnerabilities
func (sc *SecurityChecker) checkLineForVulnerabilities(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// SQL Injection patterns
	sqlInjectionPatterns := []*regexp.Regexp{
		regexp.MustCompile(`(?i).*query.*\+.*\$`),
		regexp.MustCompile(`(?i)SELECT.*\+.*WHERE`),
		regexp.MustCompile(`(?i)INSERT.*\+.*VALUES`),
		regexp.MustCompile(`(?i)UPDATE.*\+.*SET`),
		regexp.MustCompile(`(?i)DELETE.*\+.*FROM`),
	}

	for _, pattern := range sqlInjectionPatterns {
		if pattern.MatchString(line) {
			issue := models.Issue{
				Type:          models.VibeTypeSecurity,
				Severity:      models.SeverityError,
				Title:         "Potential SQL Injection vulnerability",
				Message:       "SQL query appears to use string concatenation which may lead to SQL injection",
				File:          filename,
				Line:          lineNumber,
				Rule:          "sql-injection-risk",
				Context:       utils.TruncateString(line, 100),
				Fixable:       true,
				FixSuggestion: "Use parameterized queries or prepared statements",
				Confidence:    0.8,
			}
			issues = append(issues, issue)
		}
	}

	// XSS patterns
	xssPatterns := []*regexp.Regexp{
		regexp.MustCompile(`(?i)innerHTML\s*=\s*.*\+`),
		regexp.MustCompile(`(?i)outerHTML\s*=\s*.*\+`),
		regexp.MustCompile(`(?i)document\.write\s*\(`),
	}

	for _, pattern := range xssPatterns {
		if pattern.MatchString(line) {
			issue := models.Issue{
				Type:          models.VibeTypeSecurity,
				Severity:      models.SeverityError,
				Title:         "Potential XSS vulnerability",
				Message:       "Direct DOM manipulation with user input may lead to XSS attacks",
				File:          filename,
				Line:          lineNumber,
				Rule:          "xss-risk",
				Context:       utils.TruncateString(line, 100),
				Fixable:       true,
				FixSuggestion: "Use safe DOM manipulation methods or sanitize input",
				Confidence:    0.7,
			}
			issues = append(issues, issue)
		}
	}

	// Command Injection patterns
	cmdInjectionPatterns := []*regexp.Regexp{
		regexp.MustCompile(`(?i)exec\s*\(\s*[^)]*\+`),
		regexp.MustCompile(`(?i)system\s*\(\s*[^)]*\+`),
		regexp.MustCompile(`(?i)Runtime\.exec\s*\(`),
		regexp.MustCompile(`(?i)ProcessBuilder\s*\(`),
	}

	for _, pattern := range cmdInjectionPatterns {
		if pattern.MatchString(line) {
			issue := models.Issue{
				Type:          models.VibeTypeSecurity,
				Severity:      models.SeverityError,
				Title:         "Potential Command Injection vulnerability",
				Message:       "Command execution with user input may lead to command injection",
				File:          filename,
				Line:          lineNumber,
				Rule:          "command-injection-risk",
				Context:       utils.TruncateString(line, 100),
				Fixable:       true,
				FixSuggestion: "Validate and sanitize input, use safe command execution methods",
				Confidence:    0.8,
			}
			issues = append(issues, issue)
		}
	}

	// Eval usage patterns
	evalPatterns := []*regexp.Regexp{
		regexp.MustCompile(`(?i)\beval\s*\(`),
		regexp.MustCompile(`(?i)Function\s*\(`),
		regexp.MustCompile(`(?i)setTimeout\s*\(\s*['"]\s*[^'"]*\+`),
		regexp.MustCompile(`(?i)setInterval\s*\(\s*['"]\s*[^'"]*\+`),
	}

	for _, pattern := range evalPatterns {
		if pattern.MatchString(line) {
			issue := models.Issue{
				Type:          models.VibeTypeSecurity,
				Severity:      models.SeverityWarning,
				Title:         "Dangerous eval() usage",
				Message:       "Using eval() or similar functions can lead to code injection vulnerabilities",
				File:          filename,
				Line:          lineNumber,
				Rule:          "eval-usage",
				Context:       utils.TruncateString(line, 100),
				Fixable:       true,
				FixSuggestion: "Avoid eval(), use safer alternatives like JSON.parse() for data",
				Confidence:    0.9,
			}
			issues = append(issues, issue)
		}
	}

	return issues
}

// checkLineForHardcodedCredentials checks for hardcoded passwords and credentials
func (sc *SecurityChecker) checkLineForHardcodedCredentials(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Hardcoded password patterns
	passwordPatterns := []*regexp.Regexp{
		regexp.MustCompile(`(?i)(password|pwd|pass)\s*[=:]\s*['"][^'"]{8,}['"]`),
		regexp.MustCompile(`(?i)(secret|key)\s*[=:]\s*['"][^'"]{16,}['"]`),
		regexp.MustCompile(`(?i)(token)\s*[=:]\s*['"][^'"]{20,}['"]`),
		regexp.MustCompile(`(?i)(auth|authorization)\s*[=:]\s*['"][^'"]{10,}['"]`),
	}

	for _, pattern := range passwordPatterns {
		if pattern.MatchString(line) {
			// Check if it's obviously a placeholder
			if sc.isPlaceholder(line) {
				continue
			}

			issue := models.Issue{
				Type:          models.VibeTypeSecurity,
				Severity:      models.SeverityError,
				Title:         "Hardcoded credentials detected",
				Message:       "Hardcoded passwords, keys, or tokens should not be stored in source code",
				File:          filename,
				Line:          lineNumber,
				Rule:          "hardcoded-credentials",
				Context:       utils.TruncateString(line, 100),
				Fixable:       true,
				FixSuggestion: "Use environment variables or secure configuration management",
				Confidence:    0.8,
			}
			issues = append(issues, issue)
		}
	}

	return issues
}

// checkLineForHighEntropy checks for high entropy strings that might be secrets
func (sc *SecurityChecker) checkLineForHighEntropy(filename, line string, lineNumber int) []models.Issue {
	var issues []models.Issue

	// Find quoted strings
	stringPattern := regexp.MustCompile(`['"]([A-Za-z0-9+/=]{20,})['"]`)
	matches := stringPattern.FindAllStringSubmatch(line, -1)

	for _, match := range matches {
		if len(match) > 1 {
			entropy := sc.calculateEntropy(match[1])
			if entropy > sc.entropyThreshold {
				// Check if it's a known false positive
				if sc.isHighEntropyFalsePositive(match[1]) {
					continue
				}

				issue := models.Issue{
					Type:       models.VibeTypeSecurity,
					Severity:   models.SeverityWarning,
					Title:      "High entropy string detected",
					Message:    fmt.Sprintf("String with high entropy (%.2f) may be a secret or key", entropy),
					File:       filename,
					Line:       lineNumber,
					Rule:       "high-entropy-string",
					Context:    utils.TruncateString(line, 100),
					Fixable:    false,
					Confidence: 0.6,
					Metadata: map[string]interface{}{
						"entropy": entropy,
						"string":  match[1],
					},
				}
				issues = append(issues, issue)
			}
		}
	}

	return issues
}

// calculateEntropy calculates the Shannon entropy of a string
func (sc *SecurityChecker) calculateEntropy(s string) float64 {
	if len(s) == 0 {
		return 0
	}

	// Count character frequencies
	freq := make(map[rune]int)
	for _, char := range s {
		freq[char]++
	}

	// Calculate entropy
	var entropy float64
	length := float64(len(s))

	for _, count := range freq {
		p := float64(count) / length
		if p > 0 {
			entropy -= p * math.Log2(p)
		}
	}

	return entropy
}

// isFalsePositive checks if a detected secret is a false positive
func (sc *SecurityChecker) isFalsePositive(filename, line, secretType string) bool {
	// Check common false positive patterns
	falsePositives := []string{
		"example", "test", "demo", "sample", "placeholder", "dummy",
		"fake", "mock", "template", "TODO", "FIXME", "XXX",
	}

	lowerLine := strings.ToLower(line)
	for _, fp := range falsePositives {
		if strings.Contains(lowerLine, fp) {
			return true
		}
	}

	// Check if it's in a test file
	if strings.Contains(strings.ToLower(filename), "test") ||
		strings.Contains(strings.ToLower(filename), "spec") ||
		strings.Contains(strings.ToLower(filename), "mock") {
		return true
	}

	// Check if it's in documentation
	if strings.HasSuffix(strings.ToLower(filename), ".md") ||
		strings.HasSuffix(strings.ToLower(filename), ".txt") ||
		strings.Contains(strings.ToLower(filename), "readme") {
		return true
	}

	return false
}

// isPlaceholder checks if a value is obviously a placeholder
func (sc *SecurityChecker) isPlaceholder(line string) bool {
	placeholders := []string{
		"your_password", "your_key", "your_token", "your_secret",
		"password_here", "key_here", "token_here", "secret_here",
		"enter_password", "enter_key", "enter_token",
		"12345", "abcdef", "foobar", "changeme", "replace_me",
	}

	lowerLine := strings.ToLower(line)
	for _, placeholder := range placeholders {
		if strings.Contains(lowerLine, placeholder) {
			return true
		}
	}

	return false
}

// isHighEntropyFalsePositive checks if a high entropy string is a false positive
func (sc *SecurityChecker) isHighEntropyFalsePositive(s string) bool {
	// Check for common patterns that are high entropy but not secrets

	// Base64 encoded images or data URLs
	if strings.HasPrefix(s, "data:") {
		return true
	}

	// UUIDs
	uuidPattern := regexp.MustCompile(`^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$`)
	if uuidPattern.MatchString(s) {
		return true
	}

	// Checksums or hashes (common patterns)
	if len(s) == 32 || len(s) == 40 || len(s) == 64 {
		hexPattern := regexp.MustCompile(`^[0-9a-fA-F]+$`)
		if hexPattern.MatchString(s) {
			return true
		}
	}

	return false
}

// initializeSecretPatterns initializes the secret detection patterns
func (sc *SecurityChecker) initializeSecretPatterns() {
	sc.secretPatterns = []*SecretPattern{
		{
			Name:        "OpenAI API Key",
			Pattern:     regexp.MustCompile(`sk-[a-zA-Z0-9]{48}`),
			Confidence:  0.95,
			Description: "OpenAI API key detected",
		},
		{
			Name:        "GitHub Personal Access Token",
			Pattern:     regexp.MustCompile(`ghp_[a-zA-Z0-9]{36}`),
			Confidence:  0.95,
			Description: "GitHub personal access token detected",
		},
		{
			Name:        "GitHub OAuth Token",
			Pattern:     regexp.MustCompile(`gho_[a-zA-Z0-9]{36}`),
			Confidence:  0.95,
			Description: "GitHub OAuth token detected",
		},
		{
			Name:        "GitHub Fine-grained Token",
			Pattern:     regexp.MustCompile(`github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}`),
			Confidence:  0.95,
			Description: "GitHub fine-grained personal access token detected",
		},
		{
			Name:        "Slack Bot Token",
			Pattern:     regexp.MustCompile(`xoxb-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}`),
			Confidence:  0.95,
			Description: "Slack bot token detected",
		},
		{
			Name:        "Slack App Token",
			Pattern:     regexp.MustCompile(`xoxa-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}`),
			Confidence:  0.95,
			Description: "Slack app token detected",
		},
		{
			Name:        "AWS Access Key",
			Pattern:     regexp.MustCompile(`AKIA[0-9A-Z]{16}`),
			Confidence:  0.9,
			Description: "AWS access key ID detected",
		},
		{
			Name:        "Google API Key",
			Pattern:     regexp.MustCompile(`AIza[0-9A-Za-z_-]{35}`),
			Confidence:  0.9,
			Description: "Google API key detected",
		},
		{
			Name:        "Stripe Live Secret Key",
			Pattern:     regexp.MustCompile(`sk_live_[0-9a-zA-Z]{24}`),
			Confidence:  0.95,
			Description: "Stripe live secret key detected",
		},
		{
			Name:        "Stripe Live Publishable Key",
			Pattern:     regexp.MustCompile(`pk_live_[0-9a-zA-Z]{24}`),
			Confidence:  0.95,
			Description: "Stripe live publishable key detected",
		},
		{
			Name:        "Stripe Test Secret Key",
			Pattern:     regexp.MustCompile(`sk_test_[0-9a-zA-Z]{24}`),
			Confidence:  0.8,
			Description: "Stripe test secret key detected",
		},
		{
			Name:        "Twilio API Key",
			Pattern:     regexp.MustCompile(`SK[a-z0-9]{32}`),
			Confidence:  0.8,
			Description: "Twilio API key detected",
		},
		{
			Name:        "Twilio Account SID",
			Pattern:     regexp.MustCompile(`AC[a-z0-9]{32}`),
			Confidence:  0.8,
			Description: "Twilio Account SID detected",
		},
		{
			Name:        "SendGrid API Key",
			Pattern:     regexp.MustCompile(`SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}`),
			Confidence:  0.95,
			Description: "SendGrid API key detected",
		},
		{
			Name:        "Discord Token",
			Pattern:     regexp.MustCompile(`[MN][A-Za-z\d]{23}\.[A-Za-z\d]{6}\.[A-Za-z\d_-]{27}`),
			Confidence:  0.9,
			Description: "Discord bot token detected",
		},
		{
			Name:        "Mailgun API Key",
			Pattern:     regexp.MustCompile(`key-[a-z0-9]{32}`),
			Confidence:  0.8,
			Description: "Mailgun API key detected",
		},
		{
			Name:        "Private Key",
			Pattern:     regexp.MustCompile(`-----BEGIN [A-Z]+ PRIVATE KEY-----`),
			Confidence:  0.95,
			Description: "Private key detected",
		},
		{
			Name:        "JWT Token",
			Pattern:     regexp.MustCompile(`eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*`),
			Confidence:  0.7,
			Description: "JWT token detected",
		},
	}
}

// NewVulnerabilityDB creates a new vulnerability database
func NewVulnerabilityDB() *VulnerabilityDB {
	return &VulnerabilityDB{
		patterns: make(map[string]*regexp.Regexp),
	}
}
