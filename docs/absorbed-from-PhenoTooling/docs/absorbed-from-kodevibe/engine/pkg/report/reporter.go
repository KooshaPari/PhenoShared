package report

import (
	"bytes"
	"encoding/json"
	"encoding/xml"
	"fmt"
	"html/template"
	"strings"
	"time"

	"kodevibe/internal/models"
)

// Reporter generates reports in various formats
type Reporter struct {
	config *models.Configuration
}

// NewReporter creates a new reporter instance
func NewReporter(config *models.Configuration) *Reporter {
	return &Reporter{
		config: config,
	}
}

// Generate generates a report in the specified format
func (r *Reporter) Generate(result *models.ScanResult, format string) (string, error) {
	switch strings.ToLower(format) {
	case "text":
		return r.generateTextReport(result)
	case "json":
		return r.generateJSONReport(result)
	case "html":
		return r.generateHTMLReport(result)
	case "xml":
		return r.generateXMLReport(result)
	case "junit":
		return r.generateJUnitReport(result)
	case "csv":
		return r.generateCSVReport(result)
	default:
		return "", fmt.Errorf("unsupported format: %s", format)
	}
}

// generateTextReport generates a human-readable text report
func (r *Reporter) generateTextReport(result *models.ScanResult) (string, error) {
	var buf bytes.Buffer

	// Header
	buf.WriteString("🌊 KodeVibe Scan Report\n")
	buf.WriteString(strings.Repeat("=", 50) + "\n")
	buf.WriteString(fmt.Sprintf("Scan ID: %s\n", result.ID))
	buf.WriteString(fmt.Sprintf("Started: %s\n", result.StartTime.Format(time.RFC3339)))
	buf.WriteString(fmt.Sprintf("Duration: %v\n", result.Duration))
	buf.WriteString(fmt.Sprintf("Files Scanned: %d\n", result.FilesScanned))
	buf.WriteString(fmt.Sprintf("Files Skipped: %d\n", result.FilesSkipped))
	buf.WriteString("\n")

	// Summary
	buf.WriteString("📊 Summary\n")
	buf.WriteString(strings.Repeat("-", 20) + "\n")
	buf.WriteString(fmt.Sprintf("Total Issues: %d\n", result.Summary.TotalIssues))
	buf.WriteString(fmt.Sprintf("Errors: %d\n", result.Summary.ErrorIssues))
	buf.WriteString(fmt.Sprintf("Warnings: %d\n", result.Summary.WarningIssues))
	buf.WriteString(fmt.Sprintf("Info: %d\n", result.Summary.InfoIssues))
	buf.WriteString(fmt.Sprintf("Score: %.1f (%s)\n", result.Summary.Score, result.Summary.Grade))
	buf.WriteString("\n")

	// Issues by type
	if len(result.Summary.IssuesByType) > 0 {
		buf.WriteString("🎯 Issues by Type\n")
		buf.WriteString(strings.Repeat("-", 20) + "\n")
		for vibeType, count := range result.Summary.IssuesByType {
			buf.WriteString(fmt.Sprintf("%s: %d\n", vibeType, count))
		}
		buf.WriteString("\n")
	}

	// Detailed issues
	if len(result.Issues) > 0 {
		buf.WriteString("🔍 Detailed Issues\n")
		buf.WriteString(strings.Repeat("-", 20) + "\n")

		// Group issues by type
		issuesByType := make(map[models.VibeType][]models.Issue)
		for _, issue := range result.Issues {
			issuesByType[issue.Type] = append(issuesByType[issue.Type], issue)
		}

		for vibeType, issues := range issuesByType {
			buf.WriteString(fmt.Sprintf("\n🔸 %s (%d issues)\n", vibeType, len(issues)))
			for i, issue := range issues {
				if i >= 10 { // Limit to first 10 issues per type
					buf.WriteString(fmt.Sprintf("  ... and %d more issues\n", len(issues)-10))
					break
				}
				severityIcon := r.getSeverityIcon(issue.Severity)
				buf.WriteString(fmt.Sprintf("  %s %s\n", severityIcon, issue.Title))
				buf.WriteString(fmt.Sprintf("    File: %s:%d\n", issue.File, issue.Line))
				buf.WriteString(fmt.Sprintf("    Rule: %s\n", issue.Rule))
				if issue.Message != "" {
					buf.WriteString(fmt.Sprintf("    Message: %s\n", issue.Message))
				}
				if issue.FixSuggestion != "" {
					buf.WriteString(fmt.Sprintf("    Fix: %s\n", issue.FixSuggestion))
				}
				buf.WriteString("\n")
			}
		}
	}

	return buf.String(), nil
}

// generateJSONReport generates a JSON report
func (r *Reporter) generateJSONReport(result *models.ScanResult) (string, error) {
	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal JSON: %w", err)
	}
	return string(data), nil
}

// generateHTMLReport generates an HTML report
func (r *Reporter) generateHTMLReport(result *models.ScanResult) (string, error) {
	tmpl := `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KodeVibe Scan Report</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { border-bottom: 2px solid #e1e5e9; padding-bottom: 20px; margin-bottom: 20px; }
        .title { color: #0969da; font-size: 28px; margin: 0; }
        .subtitle { color: #656d76; margin: 5px 0 0 0; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .summary-card { background: #f6f8fa; border-radius: 6px; padding: 15px; }
        .summary-title { font-weight: 600; color: #24292f; margin-bottom: 8px; }
        .summary-value { font-size: 24px; font-weight: 700; }
        .error { color: #d1242f; }
        .warning { color: #fb8500; }
        .info { color: #0969da; }
        .success { color: #1a7f37; }
        .issues { margin-top: 30px; }
        .vibe-section { margin-bottom: 30px; border: 1px solid #d1d9e0; border-radius: 6px; overflow: hidden; }
        .vibe-header { background: #f6f8fa; padding: 15px; border-bottom: 1px solid #d1d9e0; font-weight: 600; }
        .issue { padding: 15px; border-bottom: 1px solid #eaecef; }
        .issue:last-child { border-bottom: none; }
        .issue-title { font-weight: 600; margin-bottom: 5px; }
        .issue-meta { font-size: 14px; color: #656d76; }
        .issue-message { margin: 8px 0; }
        .issue-fix { background: #f6f8fa; padding: 8px; border-radius: 4px; margin-top: 8px; font-size: 14px; }
        .severity-error { border-left: 4px solid #d1242f; }
        .severity-warning { border-left: 4px solid #fb8500; }
        .severity-info { border-left: 4px solid #0969da; }
        .grade-a { color: #1a7f37; }
        .grade-b { color: #3fb950; }
        .grade-c { color: #fb8500; }
        .grade-d { color: #f85149; }
        .grade-f { color: #d1242f; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="title">🌊 KodeVibe Scan Report</h1>
            <p class="subtitle">Scan ID: {{.ID}} | Generated: {{.StartTime.Format "2006-01-02 15:04:05 UTC"}}</p>
        </div>

        <div class="summary">
            <div class="summary-card">
                <div class="summary-title">Duration</div>
                <div class="summary-value">{{.Duration}}</div>
            </div>
            <div class="summary-card">
                <div class="summary-title">Files Scanned</div>
                <div class="summary-value">{{.FilesScanned}}</div>
            </div>
            <div class="summary-card">
                <div class="summary-title">Total Issues</div>
                <div class="summary-value">{{.Summary.TotalIssues}}</div>
            </div>
            <div class="summary-card">
                <div class="summary-title">Score</div>
                <div class="summary-value grade-{{.Summary.Grade | lower}}">{{printf "%.1f" .Summary.Score}} ({{.Summary.Grade}})</div>
            </div>
        </div>

        <div class="summary">
            <div class="summary-card">
                <div class="summary-title">Errors</div>
                <div class="summary-value error">{{.Summary.ErrorCount}}</div>
            </div>
            <div class="summary-card">
                <div class="summary-title">Warnings</div>
                <div class="summary-value warning">{{.Summary.WarningCount}}</div>
            </div>
            <div class="summary-card">
                <div class="summary-title">Info</div>
                <div class="summary-value info">{{.Summary.InfoCount}}</div>
            </div>
        </div>

        {{if .Issues}}
        <div class="issues">
            {{range $vibeType, $issues := .IssuesByType}}
            <div class="vibe-section">
                <div class="vibe-header">{{$vibeType}} ({{len $issues}} issues)</div>
                {{range $issues}}
                <div class="issue severity-{{.Severity}}">
                    <div class="issue-title">{{.Title}}</div>
                    <div class="issue-meta">{{.File}}:{{.Line}} | Rule: {{.Rule}} | Severity: {{.Severity}}</div>
                    {{if .Message}}<div class="issue-message">{{.Message}}</div>{{end}}
                    {{if .FixSuggestion}}<div class="issue-fix"><strong>Fix:</strong> {{.FixSuggestion}}</div>{{end}}
                </div>
                {{end}}
            </div>
            {{end}}
        </div>
        {{end}}
    </div>
</body>
</html>`

	// Group issues by type for template
	issuesByType := make(map[models.VibeType][]models.Issue)
	for _, issue := range result.Issues {
		issuesByType[issue.Type] = append(issuesByType[issue.Type], issue)
	}

	data := struct {
		*models.ScanResult
		IssuesByType map[models.VibeType][]models.Issue
	}{
		ScanResult:   result,
		IssuesByType: issuesByType,
	}

	funcMap := template.FuncMap{
		"lower": strings.ToLower,
	}

	t, err := template.New("report").Funcs(funcMap).Parse(tmpl)
	if err != nil {
		return "", fmt.Errorf("failed to parse template: %w", err)
	}

	var buf bytes.Buffer
	if err := t.Execute(&buf, data); err != nil {
		return "", fmt.Errorf("failed to execute template: %w", err)
	}

	return buf.String(), nil
}

// generateXMLReport generates an XML report
func (r *Reporter) generateXMLReport(result *models.ScanResult) (string, error) {
	data, err := xml.MarshalIndent(result, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal XML: %w", err)
	}
	return xml.Header + string(data), nil
}

// generateJUnitReport generates a JUnit XML report
func (r *Reporter) generateJUnitReport(result *models.ScanResult) (string, error) {
	type JUnitTestCase struct {
		XMLName   xml.Name `xml:"testcase"`
		ClassName string   `xml:"classname,attr"`
		Name      string   `xml:"name,attr"`
		Time      string   `xml:"time,attr"`
		Failure   *struct {
			Message string `xml:"message,attr"`
			Text    string `xml:",chardata"`
		} `xml:"failure,omitempty"`
	}

	type JUnitTestSuite struct {
		XMLName  xml.Name        `xml:"testsuite"`
		Name     string          `xml:"name,attr"`
		Tests    int             `xml:"tests,attr"`
		Failures int             `xml:"failures,attr"`
		Time     string          `xml:"time,attr"`
		TestCase []JUnitTestCase `xml:"testcase"`
	}

	var testCases []JUnitTestCase
	failures := 0

	for _, issue := range result.Issues {
		testCase := JUnitTestCase{
			ClassName: string(issue.Type),
			Name:      issue.Rule,
			Time:      "0",
		}

		if issue.Severity == models.SeverityError {
			testCase.Failure = &struct {
				Message string `xml:"message,attr"`
				Text    string `xml:",chardata"`
			}{
				Message: issue.Title,
				Text:    fmt.Sprintf("%s:%d - %s", issue.File, issue.Line, issue.Message),
			}
			failures++
		}

		testCases = append(testCases, testCase)
	}

	suite := JUnitTestSuite{
		Name:     "KodeVibe",
		Tests:    len(testCases),
		Failures: failures,
		Time:     fmt.Sprintf("%.3f", result.Duration.Seconds()),
		TestCase: testCases,
	}

	data, err := xml.MarshalIndent(suite, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal JUnit XML: %w", err)
	}

	return xml.Header + string(data), nil
}

// generateCSVReport generates a CSV report
func (r *Reporter) generateCSVReport(result *models.ScanResult) (string, error) {
	var buf bytes.Buffer

	// Header
	buf.WriteString("Type,Severity,Rule,File,Line,Title,Message,Fix Suggestion\n")

	// Issues
	for _, issue := range result.Issues {
		buf.WriteString(fmt.Sprintf("%s,%s,%s,%s,%d,\"%s\",\"%s\",\"%s\"\n",
			issue.Type,
			issue.Severity,
			issue.Rule,
			issue.File,
			issue.Line,
			strings.ReplaceAll(issue.Title, "\"", "\"\""),
			strings.ReplaceAll(issue.Message, "\"", "\"\""),
			strings.ReplaceAll(issue.FixSuggestion, "\"", "\"\""),
		))
	}

	return buf.String(), nil
}

// getSeverityIcon returns an icon for the severity level
func (r *Reporter) getSeverityIcon(severity models.SeverityLevel) string {
	switch severity {
	case models.SeverityError:
		return "❌"
	case models.SeverityWarning:
		return "⚠️"
	case models.SeverityInfo:
		return "ℹ️"
	default:
		return "🔍"
	}
}
