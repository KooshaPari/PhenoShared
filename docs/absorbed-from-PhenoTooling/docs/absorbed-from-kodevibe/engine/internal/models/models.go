package models

import (
	"time"
)

// AnalysisResult represents the complete analysis results
type AnalysisResult struct {
	OverallScore    float64       `json:"overall_score"`
	FilesAnalyzed   int           `json:"files_analyzed"`
	LinesAnalyzed   int           `json:"lines_analyzed"`
	Duration        time.Duration `json:"duration"`
	VibeResults     []VibeResult  `json:"vibe_results"`
	Issues          []Issue       `json:"issues"`
	Recommendations []string      `json:"recommendations"`
	Timestamp       time.Time     `json:"timestamp"`
}

// VibeResult represents the result of a specific vibe analysis
type VibeResult struct {
	Name    string  `json:"name"`
	Score   float64 `json:"score"`
	Details string  `json:"details,omitempty"`
}

// SeverityLevel represents the severity of an issue
type SeverityLevel string

const (
	SeverityError    SeverityLevel = "error"
	SeverityWarning  SeverityLevel = "warning"
	SeverityInfo     SeverityLevel = "info"
	SeverityCritical SeverityLevel = "critical"
)

// VibeType represents the type of vibe check
type VibeType string

const (
	VibeTypeSecurity      VibeType = "security"
	VibeTypeCode          VibeType = "code"
	VibeTypePerformance   VibeType = "performance"
	VibeTypeFile          VibeType = "file"
	VibeTypeGit           VibeType = "git"
	VibeTypeDependency    VibeType = "dependency"
	VibeTypeDocumentation VibeType = "documentation"
)

// Issue represents a detected issue in the code
type Issue struct {
	ID            string                 `json:"id" yaml:"id"`
	Type          VibeType               `json:"type" yaml:"type"`
	Severity      SeverityLevel          `json:"severity" yaml:"severity"`
	Title         string                 `json:"title" yaml:"title"`
	Message       string                 `json:"message" yaml:"message"`
	File          string                 `json:"file" yaml:"file"`
	Line          int                    `json:"line" yaml:"line"`
	Column        int                    `json:"column" yaml:"column"`
	Rule          string                 `json:"rule" yaml:"rule"`
	Pattern       string                 `json:"pattern,omitempty" yaml:"pattern,omitempty"`
	Context       string                 `json:"context,omitempty" yaml:"context,omitempty"`
	Category      string                 `json:"category,omitempty" yaml:"category,omitempty"`
	Fix           string                 `json:"fix,omitempty" yaml:"fix,omitempty"`
	Fixable       bool                   `json:"fixable" yaml:"fixable"`
	FixSuggestion string                 `json:"fix_suggestion,omitempty" yaml:"fix_suggestion,omitempty"`
	Confidence    float64                `json:"confidence" yaml:"confidence"`
	CreatedAt     time.Time              `json:"created_at" yaml:"created_at"`
	Metadata      map[string]interface{} `json:"metadata,omitempty" yaml:"metadata,omitempty"`
}

// ScanResult represents the result of a complete scan
type ScanResult struct {
	ScanID        string                 `json:"scan_id" yaml:"scan_id"`
	ID            string                 `json:"id" yaml:"id"`
	StartTime     time.Time              `json:"start_time" yaml:"start_time"`
	EndTime       time.Time              `json:"end_time" yaml:"end_time"`
	Duration      time.Duration          `json:"duration" yaml:"duration"`
	Timestamp     time.Time              `json:"timestamp" yaml:"timestamp"`
	ProjectPath   string                 `json:"project_path" yaml:"project_path"`
	FilesScanned  int                    `json:"files_scanned" yaml:"files_scanned"`
	FilesSkipped  int                    `json:"files_skipped" yaml:"files_skipped"`
	Files         []string               `json:"files" yaml:"files"`
	Issues        []Issue                `json:"issues" yaml:"issues"`
	Summary       ScanSummary            `json:"summary" yaml:"summary"`
	Configuration *Configuration         `json:"configuration,omitempty" yaml:"configuration,omitempty"`
	Metadata      map[string]interface{} `json:"metadata,omitempty" yaml:"metadata,omitempty"`
}

// Configuration represents the KodeVibe configuration
type Configuration struct {
	Scanner      ScannerConfig             `json:"scanner" yaml:"scanner"`
	Server       ServerConfig              `json:"server" yaml:"server"`
	Vibes        map[VibeType]VibeConfig   `json:"vibes" yaml:"vibes"`
	Project      ProjectConfig             `json:"project" yaml:"project"`
	Exclude      ExcludeConfig             `json:"exclude" yaml:"exclude"`
	CustomRules  []CustomRule              `json:"custom_rules" yaml:"custom_rules"`
	Integrations IntegrationConfig         `json:"integrations" yaml:"integrations"`
	Advanced     AdvancedConfig            `json:"advanced" yaml:"advanced"`
	Languages    map[string]LanguageConfig `json:"languages" yaml:"languages"`
	CICD         CICDConfig                `json:"ci_cd" yaml:"ci_cd"`
	Reporting    ReportingConfig           `json:"reporting" yaml:"reporting"`
}

// VibeConfig represents configuration for a specific vibe
type VibeConfig struct {
	Enabled      bool                   `json:"enabled" yaml:"enabled"`
	Level        string                 `json:"level" yaml:"level"`
	Rules        []string               `json:"rules,omitempty" yaml:"rules,omitempty"`
	Checks       []string               `json:"checks,omitempty" yaml:"checks,omitempty"`
	MaxThreshold int                    `json:"max_threshold,omitempty" yaml:"max_threshold,omitempty"`
	Settings     map[string]interface{} `json:"settings,omitempty" yaml:"settings,omitempty"`
}

// ProjectConfig represents project-specific configuration
type ProjectConfig struct {
	Type        string `json:"type" yaml:"type"`
	Language    string `json:"language" yaml:"language"`
	Framework   string `json:"framework" yaml:"framework"`
	Name        string `json:"name,omitempty" yaml:"name,omitempty"`
	Description string `json:"description,omitempty" yaml:"description,omitempty"`
	Version     string `json:"version,omitempty" yaml:"version,omitempty"`
}

// ExcludeConfig represents exclusion configuration
type ExcludeConfig struct {
	Files    []string `json:"files" yaml:"files"`
	Patterns []string `json:"patterns" yaml:"patterns"`
	Paths    []string `json:"paths,omitempty" yaml:"paths,omitempty"`
}

// CustomRule represents a custom rule definition
type CustomRule struct {
	Name       string        `json:"name" yaml:"name"`
	Pattern    string        `json:"pattern" yaml:"pattern"`
	Message    string        `json:"message" yaml:"message"`
	Severity   SeverityLevel `json:"severity" yaml:"severity"`
	Type       VibeType      `json:"type" yaml:"type"`
	Enabled    bool          `json:"enabled" yaml:"enabled"`
	FileTypes  []string      `json:"file_types,omitempty" yaml:"file_types,omitempty"`
	Confidence float64       `json:"confidence" yaml:"confidence"`
}

// IntegrationConfig represents integration settings
type IntegrationConfig struct {
	Slack   SlackConfig   `json:"slack" yaml:"slack"`
	GitHub  GitHubConfig  `json:"github" yaml:"github"`
	Jira    JiraConfig    `json:"jira" yaml:"jira"`
	Teams   TeamsConfig   `json:"teams" yaml:"teams"`
	Webhook WebhookConfig `json:"webhook" yaml:"webhook"`
}

// SlackConfig represents Slack integration configuration
type SlackConfig struct {
	Enabled    bool   `json:"enabled" yaml:"enabled"`
	WebhookURL string `json:"webhook_url" yaml:"webhook_url"`
	Channel    string `json:"channel" yaml:"channel"`
	Username   string `json:"username,omitempty" yaml:"username,omitempty"`
	IconEmoji  string `json:"icon_emoji,omitempty" yaml:"icon_emoji,omitempty"`
}

// GitHubConfig represents GitHub integration configuration
type GitHubConfig struct {
	Enabled      bool   `json:"enabled" yaml:"enabled"`
	Token        string `json:"token" yaml:"token"`
	Owner        string `json:"owner" yaml:"owner"`
	Repo         string `json:"repo" yaml:"repo"`
	CreateIssues bool   `json:"create_issues" yaml:"create_issues"`
}

// JiraConfig represents Jira integration configuration
type JiraConfig struct {
	Enabled    bool   `json:"enabled" yaml:"enabled"`
	URL        string `json:"url" yaml:"url"`
	Username   string `json:"username" yaml:"username"`
	Token      string `json:"token" yaml:"token"`
	ProjectKey string `json:"project_key" yaml:"project_key"`
}

// TeamsConfig represents Microsoft Teams integration configuration
type TeamsConfig struct {
	Enabled    bool   `json:"enabled" yaml:"enabled"`
	WebhookURL string `json:"webhook_url" yaml:"webhook_url"`
}

// WebhookConfig represents generic webhook configuration
type WebhookConfig struct {
	Enabled bool              `json:"enabled" yaml:"enabled"`
	URL     string            `json:"url" yaml:"url"`
	Headers map[string]string `json:"headers,omitempty" yaml:"headers,omitempty"`
}

// AdvancedConfig represents advanced configuration options
type AdvancedConfig struct {
	EntropyAnalysis      bool              `json:"entropy_analysis" yaml:"entropy_analysis"`
	EntropyThreshold     float64           `json:"entropy_threshold" yaml:"entropy_threshold"`
	AIDetection          bool              `json:"ai_detection" yaml:"ai_detection"`
	AIProvider           string            `json:"ai_provider" yaml:"ai_provider"`
	AIModel              string            `json:"ai_model" yaml:"ai_model"`
	ExternalScanners     []ExternalScanner `json:"external_scanners" yaml:"external_scanners"`
	PerformanceProfiling bool              `json:"performance_profiling" yaml:"performance_profiling"`
	CacheEnabled         bool              `json:"cache_enabled" yaml:"cache_enabled"`
	CacheTTL             time.Duration     `json:"cache_ttl" yaml:"cache_ttl"`
	MaxConcurrency       int               `json:"max_concurrency" yaml:"max_concurrency"`
	Timeout              time.Duration     `json:"timeout" yaml:"timeout"`
	CustomAnalyzers      []CustomAnalyzer  `json:"custom_analyzers" yaml:"custom_analyzers"`
}

// ExternalScanner represents external scanner configuration
type ExternalScanner struct {
	Name    string   `json:"name" yaml:"name"`
	Enabled bool     `json:"enabled" yaml:"enabled"`
	Command string   `json:"command" yaml:"command"`
	Args    []string `json:"args,omitempty" yaml:"args,omitempty"`
}

// CustomAnalyzer represents custom analyzer configuration
type CustomAnalyzer struct {
	Name    string `json:"name" yaml:"name"`
	Enabled bool   `json:"enabled" yaml:"enabled"`
	Script  string `json:"script" yaml:"script"`
	Type    string `json:"type" yaml:"type"`
}

// LanguageConfig represents language-specific configuration
type LanguageConfig struct {
	Analyzers         []string               `json:"analyzers" yaml:"analyzers"`
	PerformanceChecks []string               `json:"performance_checks" yaml:"performance_checks"`
	SecurityChecks    []string               `json:"security_checks" yaml:"security_checks"`
	CodeStyle         []string               `json:"code_style" yaml:"code_style"`
	Settings          map[string]interface{} `json:"settings,omitempty" yaml:"settings,omitempty"`
}

// CICDConfig represents CI/CD integration configuration
type CICDConfig struct {
	GitHubActions GitHubActionsConfig `json:"github_actions" yaml:"github_actions"`
	GitLabCI      GitLabCIConfig      `json:"gitlab_ci" yaml:"gitlab_ci"`
	Jenkins       JenkinsConfig       `json:"jenkins" yaml:"jenkins"`
	QualityGates  QualityGatesConfig  `json:"quality_gates" yaml:"quality_gates"`
}

// GitHubActionsConfig represents GitHub Actions configuration
type GitHubActionsConfig struct {
	Enabled bool            `json:"enabled" yaml:"enabled"`
	FailOn  []SeverityLevel `json:"fail_on" yaml:"fail_on"`
}

// GitLabCIConfig represents GitLab CI configuration
type GitLabCIConfig struct {
	Enabled bool `json:"enabled" yaml:"enabled"`
}

// JenkinsConfig represents Jenkins configuration
type JenkinsConfig struct {
	Enabled bool `json:"enabled" yaml:"enabled"`
}

// QualityGatesConfig represents quality gates configuration
type QualityGatesConfig struct {
	MinCodeCoverage      int `json:"min_code_coverage" yaml:"min_code_coverage"`
	MaxComplexityScore   int `json:"max_complexity_score" yaml:"max_complexity_score"`
	MaxSecurityIssues    int `json:"max_security_issues" yaml:"max_security_issues"`
	MaxPerformanceIssues int `json:"max_performance_issues" yaml:"max_performance_issues"`
}

// ReportingConfig represents reporting configuration
type ReportingConfig struct {
	GenerateReports bool              `json:"generate_reports" yaml:"generate_reports"`
	ReportFormat    string            `json:"report_format" yaml:"report_format"`
	ReportPath      string            `json:"report_path" yaml:"report_path"`
	Logging         LoggingConfig     `json:"logging" yaml:"logging"`
	Templates       map[string]string `json:"templates,omitempty" yaml:"templates,omitempty"`
}

// LoggingConfig represents logging configuration
type LoggingConfig struct {
	Enabled bool   `json:"enabled" yaml:"enabled"`
	Level   string `json:"level" yaml:"level"`
	Format  string `json:"format" yaml:"format"`
	File    string `json:"file" yaml:"file"`
}

// ScanRequest represents a request to scan files
type ScanRequest struct {
	ID         string         `json:"id" yaml:"id"`
	Paths      []string       `json:"paths" yaml:"paths"`
	Vibes      []string       `json:"vibes" yaml:"vibes"`
	Config     *Configuration `json:"config,omitempty" yaml:"config,omitempty"`
	StagedOnly bool           `json:"staged_only" yaml:"staged_only"`
	DiffTarget string         `json:"diff_target,omitempty" yaml:"diff_target,omitempty"`
	Format     ReportFormat   `json:"format" yaml:"format"`
	CreatedAt  time.Time      `json:"created_at" yaml:"created_at"`
}

// FixResult represents the result of an auto-fix operation
type FixResult struct {
	IssueID      string    `json:"issue_id" yaml:"issue_id"`
	Fixed        bool      `json:"fixed" yaml:"fixed"`
	OriginalCode string    `json:"original_code" yaml:"original_code"`
	FixedCode    string    `json:"fixed_code" yaml:"fixed_code"`
	Error        string    `json:"error,omitempty" yaml:"error,omitempty"`
	Confidence   float64   `json:"confidence" yaml:"confidence"`
	AppliedAt    time.Time `json:"applied_at" yaml:"applied_at"`
}

// WatchEvent represents a file system event
type WatchEvent struct {
	Path      string    `json:"path" yaml:"path"`
	Operation string    `json:"operation" yaml:"operation"`
	Timestamp time.Time `json:"timestamp" yaml:"timestamp"`
}

// ProfileResult represents performance profiling results
type ProfileResult struct {
	Tool            string                 `json:"tool" yaml:"tool"`
	Metrics         map[string]interface{} `json:"metrics" yaml:"metrics"`
	Score           float64                `json:"score" yaml:"score"`
	Recommendations []string               `json:"recommendations" yaml:"recommendations"`
	Timestamp       time.Time              `json:"timestamp" yaml:"timestamp"`
}

// ServerConfig represents server configuration
type ServerConfig struct {
	Host       string           `json:"host" yaml:"host"`
	Port       int              `json:"port" yaml:"port"`
	TLS        bool             `json:"tls" yaml:"tls"`
	CertFile   string           `json:"cert_file,omitempty" yaml:"cert_file,omitempty"`
	KeyFile    string           `json:"key_file,omitempty" yaml:"key_file,omitempty"`
	Auth       AuthConfig       `json:"auth" yaml:"auth"`
	RateLimit  RateLimitConfig  `json:"rate_limit" yaml:"rate_limit"`
	CORS       CORSConfig       `json:"cors" yaml:"cors"`
	Monitoring MonitoringConfig `json:"monitoring" yaml:"monitoring"`
}

// AuthConfig represents authentication configuration
type AuthConfig struct {
	Enabled  bool          `json:"enabled" yaml:"enabled"`
	Type     string        `json:"type" yaml:"type"`
	Secret   string        `json:"secret" yaml:"secret"`
	TokenTTL time.Duration `json:"token_ttl" yaml:"token_ttl"`
}

// RateLimitConfig represents rate limiting configuration
type RateLimitConfig struct {
	Enabled bool `json:"enabled" yaml:"enabled"`
	RPS     int  `json:"rps" yaml:"rps"`
	Burst   int  `json:"burst" yaml:"burst"`
}

// CORSConfig represents CORS configuration
type CORSConfig struct {
	Enabled        bool     `json:"enabled" yaml:"enabled"`
	AllowedOrigins []string `json:"allowed_origins" yaml:"allowed_origins"`
	AllowedMethods []string `json:"allowed_methods" yaml:"allowed_methods"`
	AllowedHeaders []string `json:"allowed_headers" yaml:"allowed_headers"`
}

// MonitoringConfig represents monitoring configuration
type MonitoringConfig struct {
	Enabled     bool   `json:"enabled" yaml:"enabled"`
	Prometheus  bool   `json:"prometheus" yaml:"prometheus"`
	Grafana     bool   `json:"grafana" yaml:"grafana"`
	HealthCheck bool   `json:"health_check" yaml:"health_check"`
	MetricsPath string `json:"metrics_path" yaml:"metrics_path"`
}

// ReportFormat represents different report output formats
type ReportFormat string

const (
	ReportFormatText  ReportFormat = "text"
	ReportFormatJSON  ReportFormat = "json"
	ReportFormatHTML  ReportFormat = "html"
	ReportFormatXML   ReportFormat = "xml"
	ReportFormatJUnit ReportFormat = "junit"
	ReportFormatCSV   ReportFormat = "csv"
)

// ScannerConfig represents scanner configuration
type ScannerConfig struct {
	MaxConcurrency  int      `json:"max_concurrency" yaml:"max_concurrency"`
	Timeout         int      `json:"timeout" yaml:"timeout"`
	EnabledVibes    []string `json:"enabled_vibes" yaml:"enabled_vibes"`
	ExcludePatterns []string `json:"exclude_patterns" yaml:"exclude_patterns"`
}

// Issue validation method
func (i *Issue) IsValid() bool {
	if i.Title == "" || i.Message == "" || i.File == "" {
		return false
	}
	if i.Line <= 0 {
		return false
	}
	if i.Confidence < 0 || i.Confidence > 1 {
		return false
	}
	return true
}

// ScanRequest validation method
func (sr *ScanRequest) IsValid() bool {
	if len(sr.Paths) == 0 || len(sr.Vibes) == 0 {
		return false
	}
	for _, path := range sr.Paths {
		if path == "" {
			return false
		}
	}
	for _, vibe := range sr.Vibes {
		if vibe == "" {
			return false
		}
	}
	return true
}

// ScanResult helper methods
func (sr *ScanResult) CalculateSummary() ScanSummary {
	summary := ScanSummary{
		TotalIssues:  len(sr.Issues),
		IssuesByType: make(map[VibeType]int),
		FilesScanned: 0,
	}

	filesMap := make(map[string]bool)

	for _, issue := range sr.Issues {
		// Count by severity
		switch issue.Severity {
		case SeverityCritical:
			summary.CriticalIssues++
		case SeverityError:
			summary.ErrorIssues++
		case SeverityWarning:
			summary.WarningIssues++
		case SeverityInfo:
			summary.InfoIssues++
		}

		// Count by type
		summary.IssuesByType[issue.Type]++

		// Count unique files
		filesMap[issue.File] = true
	}

	summary.FilesScanned = len(filesMap)
	return summary
}

func (sr *ScanResult) GetIssuesBySeverity(severity SeverityLevel) []Issue {
	var result []Issue
	for _, issue := range sr.Issues {
		if issue.Severity == severity {
			result = append(result, issue)
		}
	}
	return result
}

func (sr *ScanResult) GetIssuesByType(vibeType VibeType) []Issue {
	var result []Issue
	for _, issue := range sr.Issues {
		if issue.Type == vibeType {
			result = append(result, issue)
		}
	}
	return result
}

func (sr *ScanResult) GetIssuesByFile(filename string) []Issue {
	var result []Issue
	for _, issue := range sr.Issues {
		if issue.File == filename {
			result = append(result, issue)
		}
	}
	return result
}

// Configuration validation method
func (c *Configuration) IsValid() bool {
	// Basic scanner validation
	if c.Scanner.MaxConcurrency <= 0 {
		return false
	}
	if c.Scanner.Timeout < 0 {
		return false
	}

	// Basic server validation
	if c.Server.Port <= 0 || c.Server.Port > 65535 {
		return false
	}

	return true
}

// VibeConfig helper method
func (vc *VibeConfig) IsEnabled() bool {
	return vc.Enabled
}

// ScanSummary structure updates
type ScanSummary struct {
	TotalIssues      int                   `json:"total_issues" yaml:"total_issues"`
	CriticalIssues   int                   `json:"critical_issues" yaml:"critical_issues"`
	CriticalCount    int                   `json:"critical_count" yaml:"critical_count"`
	ErrorIssues      int                   `json:"error_issues" yaml:"error_issues"`
	ErrorCount       int                   `json:"error_count" yaml:"error_count"`
	WarningIssues    int                   `json:"warning_issues" yaml:"warning_issues"`
	WarningCount     int                   `json:"warning_count" yaml:"warning_count"`
	InfoIssues       int                   `json:"info_issues" yaml:"info_issues"`
	InfoCount        int                   `json:"info_count" yaml:"info_count"`
	FilesScanned     int                   `json:"files_scanned" yaml:"files_scanned"`
	IssuesByType     map[VibeType]int      `json:"issues_by_type" yaml:"issues_by_type"`
	IssuesBySeverity map[SeverityLevel]int `json:"issues_by_severity" yaml:"issues_by_severity"`
	TopIssues        []string              `json:"top_issues" yaml:"top_issues"`
	Score            float64               `json:"score" yaml:"score"`
	Grade            string                `json:"grade" yaml:"grade"`
}
