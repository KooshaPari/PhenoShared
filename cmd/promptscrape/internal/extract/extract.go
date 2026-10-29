package extract

import (
	"fmt"
	"regexp"
	"strings"
)

var codexUUIDRe = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)

// jcodeSessionRe matches a JCode session id such as session_pig_1792638703385_34d0c212ece1d6b9.
var jcodeSessionRe = regexp.MustCompile(`^session_[a-z]+_\d{13}_[0-9a-f]{16}$`)

// Extract pulls the prompt timeline for a session id.
//
// The session id decides the source: a JCode id reads the JCode session store,
// a Codex UUID reads the Codex thread history. When the id shape is ambiguous
// both sources are tried and the one that yields prompts wins.
func Extract(sessionID string) (*Timeline, error) {
	sessionID = strings.TrimSpace(sessionID)
	if sessionID == "" {
		return nil, fmt.Errorf("session id is empty")
	}

	switch {
	case jcodeSessionRe.MatchString(sessionID):
		prompts, err := extractJCode(sessionID)
		if err != nil {
			return nil, err
		}
		return &Timeline{SessionID: sessionID, Source: "jcode", Prompts: prompts}, nil

	case codexUUIDRe.MatchString(sessionID):
		prompts, err := extractCodexSQLite(sessionID)
		if err != nil || len(prompts) == 0 {
			rolloutPrompts, rolloutErr := extractCodexRollout(sessionID)
			if rolloutErr == nil && len(rolloutPrompts) > 0 {
				return &Timeline{SessionID: sessionID, Source: "codex-rollout", Prompts: rolloutPrompts}, nil
			}
			if err != nil {
				return nil, err
			}
			return &Timeline{SessionID: sessionID, Source: "codex", Prompts: nil}, nil
		}
		return &Timeline{SessionID: sessionID, Source: "codex-sqlite", Prompts: prompts}, nil
	}

	// Unknown shape: try JCode, then Codex.
	if prompts, err := extractJCode(sessionID); err == nil && len(prompts) > 0 {
		return &Timeline{SessionID: sessionID, Source: "jcode", Prompts: prompts}, nil
	}
	if prompts, err := extractCodexSQLite(sessionID); err == nil && len(prompts) > 0 {
		return &Timeline{SessionID: sessionID, Source: "codex-sqlite", Prompts: prompts}, nil
	}
	if prompts, err := extractCodexRollout(sessionID); err == nil && len(prompts) > 0 {
		return &Timeline{SessionID: sessionID, Source: "codex-rollout", Prompts: prompts}, nil
	}
	return nil, fmt.Errorf("no prompts found for session %s", sessionID)
}
