package extract

import (
	"regexp"
	"strings"
)

var codexUUIDRe = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)

func Extract(sessionID string) ([]Prompt, error) {
	if strings.HasPrefix(sessionID, "session_") {
		return extractJCode(sessionID)
	}
	if codexUUIDRe.MatchString(sessionID) {
		// Try sqlite first
		prompts, err := extractCodexSQLite(sessionID)
		if err == nil && len(prompts) > 0 {
			return prompts, nil
		}
		return extractCodexRollout(sessionID)
	}
	// Try as JCode anyway
	prompts, err := extractJCode(sessionID)
	if err == nil && len(prompts) > 0 {
		return prompts, nil
	}
	return extractCodexSQLite(sessionID)
}
