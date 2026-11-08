package vibes

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

	"kodevibe/internal/models"
	"kodevibe/internal/utils"
)

// FileChecker implements file organization checks
type FileChecker struct {
	config models.VibeConfig
}

// NewFileChecker creates a new file checker
func NewFileChecker() *FileChecker {
	return &FileChecker{}
}

func (fc *FileChecker) Name() string                             { return "FileVibe" }
func (fc *FileChecker) Type() models.VibeType                    { return models.VibeTypeFile }
func (fc *FileChecker) Configure(config models.VibeConfig) error { fc.config = config; return nil }
func (fc *FileChecker) Supports(filename string) bool            { return true }

func (fc *FileChecker) Check(ctx context.Context, files []string) ([]models.Issue, error) {
	var issues []models.Issue

	for _, file := range files {
		fileIssues := fc.checkFile(file)
		issues = append(issues, fileIssues...)
	}

	return issues, nil
}

func (fc *FileChecker) checkFile(filename string) []models.Issue {
	var issues []models.Issue

	// Check for system junk files
	basename := filepath.Base(filename)
	junkFiles := []string{".DS_Store", "Thumbs.db", "desktop.ini", "._.DS_Store"}
	for _, junk := range junkFiles {
		if basename == junk {
			issue := models.Issue{
				Type:          models.VibeTypeFile,
				Severity:      models.SeverityWarning,
				Title:         "System junk file",
				Message:       fmt.Sprintf("System file '%s' should not be committed", basename),
				File:          filename,
				Line:          1,
				Rule:          "system-junk-files",
				Fixable:       true,
				FixSuggestion: "Add to .gitignore and remove from repository",
				Confidence:    1.0,
			}
			issues = append(issues, issue)
		}
	}

	// Check file size
	if info, err := os.Stat(filename); err == nil {
		if info.Size() > 10*1024*1024 { // 10MB
			issue := models.Issue{
				Type:          models.VibeTypeFile,
				Severity:      models.SeverityWarning,
				Title:         "Large file detected",
				Message:       fmt.Sprintf("File size (%s) is very large", utils.FormatSize(info.Size())),
				File:          filename,
				Line:          1,
				Rule:          "large-file-size",
				Fixable:       false,
				FixSuggestion: "Consider if this large file should be tracked in version control",
				Confidence:    0.8,
			}
			issues = append(issues, issue)
		}
	}

	return issues
}
