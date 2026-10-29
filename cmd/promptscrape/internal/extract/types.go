package extract

// Prompt is one real user prompt extracted from a harness session.
//
// Invariants that every extractor must uphold:
//   - Text is the verbatim prompt body as the human typed it.
//   - Timestamp is RFC3339 in UTC, empty only when the source carries none.
//   - ID is the harness-native message/item identifier, stable across re-runs.
type Prompt struct {
	ID        string `json:"id"`
	Timestamp string `json:"timestamp"`
	Text      string `json:"text"`
}

// Timeline is the full extraction result for one session.
type Timeline struct {
	SessionID string   `json:"session_id"`
	Source    string   `json:"source"`
	Prompts   []Prompt `json:"prompts"`
}
