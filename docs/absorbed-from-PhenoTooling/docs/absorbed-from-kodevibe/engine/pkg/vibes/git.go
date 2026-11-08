package vibes

import (
	"context"

	"kodevibe/internal/models"
)

// GitChecker implements git-related checks
type GitChecker struct {
	config models.VibeConfig
}

func NewGitChecker() *GitChecker                                { return &GitChecker{} }
func (gc *GitChecker) Name() string                             { return "GitVibe" }
func (gc *GitChecker) Type() models.VibeType                    { return models.VibeTypeGit }
func (gc *GitChecker) Configure(config models.VibeConfig) error { gc.config = config; return nil }
func (gc *GitChecker) Supports(filename string) bool            { return true }

func (gc *GitChecker) Check(ctx context.Context, files []string) ([]models.Issue, error) {
	// Git checks would typically examine commit messages, branch names, etc.
	// For now, return empty - would need git integration
	return []models.Issue{}, nil
}
