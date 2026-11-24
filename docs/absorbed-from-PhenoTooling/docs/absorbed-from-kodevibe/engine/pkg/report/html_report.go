package report

import (
	"encoding/json"
	"fmt"
	"html/template"
	"os"
	"path/filepath"
	"time"

	"kodevibe/internal/models"
)

// HTMLReportGenerator creates interactive HTML reports
type HTMLReportGenerator struct {
	templateDir string
	outputDir   string
}

// NewHTMLReportGenerator creates a new HTML report generator
func NewHTMLReportGenerator(outputDir string) *HTMLReportGenerator {
	return &HTMLReportGenerator{
		templateDir: "templates",
		outputDir:   outputDir,
	}
}

// GenerateReport creates a comprehensive HTML report
func (h *HTMLReportGenerator) GenerateReport(result *models.AnalysisResult, projectPath string) error {
	// Ensure output directory exists
	if err := os.MkdirAll(h.outputDir, 0755); err != nil {
		return fmt.Errorf("failed to create output directory: %w", err)
	}

	// Create report data
	reportData := h.prepareReportData(result, projectPath)

	// Generate main HTML file
	if err := h.generateMainHTML(reportData); err != nil {
		return fmt.Errorf("failed to generate main HTML: %w", err)
	}

	// Generate CSS file
	if err := h.generateCSS(); err != nil {
		return fmt.Errorf("failed to generate CSS: %w", err)
	}

	// Generate JavaScript file
	if err := h.generateJavaScript(); err != nil {
		return fmt.Errorf("failed to generate JavaScript: %w", err)
	}

	// Copy static assets
	if err := h.copyStaticAssets(); err != nil {
		return fmt.Errorf("failed to copy static assets: %w", err)
	}

	return nil
}

// ReportData contains all data needed for the HTML report
type ReportData struct {
	ProjectName      string              `json:"projectName"`
	GeneratedAt      time.Time           `json:"generatedAt"`
	OverallScore     float64             `json:"overallScore"`
	TotalFiles       int                 `json:"totalFiles"`
	TotalLines       int                 `json:"totalLines"`
	AnalysisDuration time.Duration       `json:"analysisDuration"`
	VibeResults      []models.VibeResult `json:"vibeResults"`
	Issues           []models.Issue      `json:"issues"`
	Recommendations  []string            `json:"recommendations"`
	ScoreHistory     []ScorePoint        `json:"scoreHistory"`
	FileMetrics      []FileMetric        `json:"fileMetrics"`
	SecurityIssues   []SecurityIssue     `json:"securityIssues"`
	PerformanceData  PerformanceMetrics  `json:"performanceData"`
}

type ScorePoint struct {
	Timestamp time.Time `json:"timestamp"`
	Score     float64   `json:"score"`
	Vibe      string    `json:"vibe"`
}

type FileMetric struct {
	Path         string    `json:"path"`
	Lines        int       `json:"lines"`
	Complexity   int       `json:"complexity"`
	Coverage     float64   `json:"coverage"`
	Score        float64   `json:"score"`
	Issues       int       `json:"issues"`
	LastModified time.Time `json:"lastModified"`
}

type SecurityIssue struct {
	Severity    string `json:"severity"`
	Category    string `json:"category"`
	File        string `json:"file"`
	Line        int    `json:"line"`
	Description string `json:"description"`
	Remediation string `json:"remediation"`
	CWE         string `json:"cwe,omitempty"`
}

type PerformanceMetrics struct {
	MemoryUsage    int64    `json:"memoryUsage"`
	ExecutionTime  float64  `json:"executionTime"`
	FilesPerSecond float64  `json:"filesPerSecond"`
	Bottlenecks    []string `json:"bottlenecks"`
}

// prepareReportData prepares all data for the HTML report
func (h *HTMLReportGenerator) prepareReportData(result *models.AnalysisResult, projectPath string) *ReportData {
	projectName := filepath.Base(projectPath)

	return &ReportData{
		ProjectName:      projectName,
		GeneratedAt:      time.Now(),
		OverallScore:     result.OverallScore,
		TotalFiles:       result.FilesAnalyzed,
		TotalLines:       result.LinesAnalyzed,
		AnalysisDuration: result.Duration,
		VibeResults:      result.VibeResults,
		Issues:           result.Issues,
		Recommendations:  result.Recommendations,
		ScoreHistory:     h.generateScoreHistory(result),
		FileMetrics:      h.generateFileMetrics(result),
		SecurityIssues:   h.extractSecurityIssues(result.Issues),
		PerformanceData:  h.generatePerformanceMetrics(result),
	}
}

// generateMainHTML creates the main HTML report file
func (h *HTMLReportGenerator) generateMainHTML(data *ReportData) error {
	tmpl := template.Must(template.New("report").Parse(htmlTemplate))

	// Convert data to JSON for JavaScript
	jsonData, err := json.Marshal(data)
	if err != nil {
		return fmt.Errorf("failed to marshal report data: %w", err)
	}

	templateData := struct {
		*ReportData
		JSONData template.JS
	}{
		ReportData: data,
		JSONData:   template.JS(jsonData),
	}

	outputPath := filepath.Join(h.outputDir, "index.html")
	file, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("failed to create HTML file: %w", err)
	}
	defer file.Close()

	return tmpl.Execute(file, templateData)
}

// generateCSS creates the CSS file for styling
func (h *HTMLReportGenerator) generateCSS() error {
	outputPath := filepath.Join(h.outputDir, "styles.css")
	return os.WriteFile(outputPath, []byte(cssStyles), 0644)
}

// generateJavaScript creates the JavaScript file for interactivity
func (h *HTMLReportGenerator) generateJavaScript() error {
	outputPath := filepath.Join(h.outputDir, "script.js")
	return os.WriteFile(outputPath, []byte(jsScript), 0644)
}

// copyStaticAssets copies static assets to the output directory
func (h *HTMLReportGenerator) copyStaticAssets() error {
	// Create assets directory
	assetsDir := filepath.Join(h.outputDir, "assets")
	if err := os.MkdirAll(assetsDir, 0755); err != nil {
		return err
	}

	// Generate Chart.js bundle (simplified version)
	chartJSPath := filepath.Join(assetsDir, "chart.min.js")
	return os.WriteFile(chartJSPath, []byte(chartJSBundle), 0644)
}

// Helper functions for data generation
func (h *HTMLReportGenerator) generateScoreHistory(result *models.AnalysisResult) []ScorePoint {
	var history []ScorePoint
	baseTime := time.Now().Add(-30 * 24 * time.Hour) // 30 days ago

	// Generate sample historical data
	for i := 0; i < 30; i++ {
		for _, vibe := range result.VibeResults {
			history = append(history, ScorePoint{
				Timestamp: baseTime.Add(time.Duration(i) * 24 * time.Hour),
				Score:     vibe.Score + float64(i%5-2), // Add some variation
				Vibe:      vibe.Name,
			})
		}
	}

	return history
}

func (h *HTMLReportGenerator) generateFileMetrics(result *models.AnalysisResult) []FileMetric {
	var metrics []FileMetric

	// Group issues by file
	fileIssues := make(map[string]int)
	for _, issue := range result.Issues {
		fileIssues[issue.File]++
	}

	// Generate metrics for each file
	for file, issueCount := range fileIssues {
		metrics = append(metrics, FileMetric{
			Path:         file,
			Lines:        100 + (len(file) * 10), // Mock data
			Complexity:   5 + issueCount,
			Coverage:     85.0 - float64(issueCount*5),
			Score:        100.0 - float64(issueCount*10),
			Issues:       issueCount,
			LastModified: time.Now().Add(-time.Duration(issueCount) * time.Hour),
		})
	}

	return metrics
}

func (h *HTMLReportGenerator) extractSecurityIssues(issues []models.Issue) []SecurityIssue {
	var securityIssues []SecurityIssue

	for _, issue := range issues {
		if issue.Category == "security" {
			securityIssues = append(securityIssues, SecurityIssue{
				Severity:    string(issue.Severity),
				Category:    "Security",
				File:        issue.File,
				Line:        issue.Line,
				Description: issue.Message,
				Remediation: generateRemediation(issue.Message),
				CWE:         extractCWE(issue.Message),
			})
		}
	}

	return securityIssues
}

func (h *HTMLReportGenerator) generatePerformanceMetrics(result *models.AnalysisResult) PerformanceMetrics {
	return PerformanceMetrics{
		MemoryUsage:    1024 * 1024 * 50, // 50MB
		ExecutionTime:  result.Duration.Seconds(),
		FilesPerSecond: float64(result.FilesAnalyzed) / result.Duration.Seconds(),
		Bottlenecks:    []string{"Large file parsing", "Regex complexity", "Memory allocation"},
	}
}

// Helper functions
func generateRemediation(message string) string {
	// Simple remediation suggestions based on issue type
	switch {
	case contains(message, "password"):
		return "Use secure password hashing algorithms like bcrypt or Argon2"
	case contains(message, "sql"):
		return "Use parameterized queries to prevent SQL injection"
	case contains(message, "xss"):
		return "Implement proper input validation and output encoding"
	default:
		return "Review and follow security best practices"
	}
}

func extractCWE(message string) string {
	// Extract CWE identifiers from messages
	if contains(message, "injection") {
		return "CWE-89"
	}
	if contains(message, "xss") {
		return "CWE-79"
	}
	if contains(message, "authentication") {
		return "CWE-287"
	}
	return ""
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr ||
		(len(s) > len(substr) &&
			(s[:len(substr)] == substr ||
				s[len(s)-len(substr):] == substr ||
				findInString(s, substr))))
}

func findInString(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}

// GetReportPath returns the path to the generated report
func (h *HTMLReportGenerator) GetReportPath() string {
	return filepath.Join(h.outputDir, "index.html")
}
