package vibes

import (
	"context"

	"kodevibe/internal/models"
)

// DocumentationChecker implements documentation-related checks
type DocumentationChecker struct {
	config models.VibeConfig
}

func NewDocumentationChecker() *DocumentationChecker   { return &DocumentationChecker{} }
func (dc *DocumentationChecker) Name() string          { return "DocumentationVibe" }
func (dc *DocumentationChecker) Type() models.VibeType { return models.VibeTypeDocumentation }
func (dc *DocumentationChecker) Configure(config models.VibeConfig) error {
	dc.config = config
	return nil
}
func (dc *DocumentationChecker) Supports(filename string) bool { return false } // Would check for missing docs

func (dc *DocumentationChecker) Check(ctx context.Context, files []string) ([]models.Issue, error) {
	// Would check for missing README, API docs, comments, etc.
	return []models.Issue{}, nil
}
