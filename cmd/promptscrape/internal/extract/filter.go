package extract

import "strings"

// injectedPrefixes are harness-injected context blocks that are not user prompts.
//
// These arrive attached to the user turn but were never typed by the human.
// They must never appear in a curate/annotate/label timeline.
var injectedPrefixes = []string{
	"<environment_context>",
	"<permissions instructions>",
	"<user_instructions>",
	"<system-reminder>",
	"<agents_md>",
	"# AGENTS.md",
	"<project_context>",
	"<environment>",
}

// continuationPrefixes mark messages the harness generated to continue a turn.
var continuationPrefixes = []string{
	"<|",
	"<turn_aborted>",
	"<user_inst>",
}

// transcriptMarkers identify agent-output lines inside a rendered transcript.
//
// Codex resumes a session by replaying the whole rendered turn -- the agent's
// bullets, its tool transcripts, and the human's own input -- into a single
// "user" message. When that happens the human's instruction survives as a line
// prefixed with the TUI prompt marker, and everything else is replay noise.
var transcriptMarkers = []string{
	"•", // agent bullet
	"└", // tool tree branch
	"│", // tool tree trunk
	"─", // horizontal rule
	"Explored",
	"Ran ",
	"Read ",
	"Edited ",
	"Grepped ",
	"Updated ",
	"Command completed",
	"Background task",
}

// isInjected reports whether text is harness-injected context rather than a human prompt.
func isInjected(text string) bool {
	trimmed := strings.TrimSpace(text)
	for _, p := range injectedPrefixes {
		if strings.HasPrefix(trimmed, p) {
			return true
		}
	}
	return false
}

// isContinuation reports whether text is a harness continuation marker.
func isContinuation(text string) bool {
	trimmed := strings.TrimSpace(text)
	for _, p := range continuationPrefixes {
		if strings.HasPrefix(trimmed, p) {
			return true
		}
	}
	return false
}

// isTranscriptReplay reports whether text is a rendered agent transcript.
//
// A replay contains the agent's own output. When it does, only the human's
// input lines are signal and the rest must be discarded.
func isTranscriptReplay(text string) bool {
	for _, line := range strings.Split(text, "\n") {
		trimmed := strings.TrimSpace(line)
		if trimmed == "" {
			continue
		}
		for _, marker := range transcriptMarkers {
			if strings.HasPrefix(trimmed, marker) {
				return true
			}
		}
	}
	return false
}

// humanPromptMarker is the TUI prompt marker that precedes a human input line
// inside a rendered transcript.
const humanPromptMarker = "›"

// extractHumanLines pulls the human's own input out of a rendered transcript.
//
// Codex stores a resumed turn as the full rendered screen. The human's actual
// instructions are the lines prefixed with the TUI prompt marker; everything
// else is the agent's output and must not reach a curation timeline.
//
// A replay can pack many separate prompts into one stored message, so each
// marked line is returned on its own.
func extractHumanLines(text string) []string {
	var lines []string
	for _, line := range strings.Split(text, "\n") {
		trimmed := strings.TrimSpace(line)
		if !strings.HasPrefix(trimmed, humanPromptMarker) {
			continue
		}
		human := strings.TrimSpace(strings.TrimPrefix(trimmed, humanPromptMarker))
		// A doubled marker means the human typed a marker character themselves.
		human = strings.TrimSpace(strings.TrimPrefix(human, humanPromptMarker))
		if human == "" {
			continue
		}
		lines = append(lines, human)
	}
	return lines
}

// normalizePrompt applies the shared acceptance rules to a candidate user message.
//
// It returns the prompts to keep, one per human input, and whether to keep any:
//
//   - Harness-injected context (environment_context, permissions, AGENTS.md) is dropped.
//   - Harness continuation markers are dropped.
//   - A rendered transcript is reduced to the human's own input lines; if it has
//     none, it is dropped entirely.
//   - Anything else is kept verbatim as a single prompt.
func normalizePrompt(text string) ([]string, bool) {
	trimmed := strings.TrimSpace(text)
	if trimmed == "" {
		return nil, false
	}
	if isInjected(trimmed) || isContinuation(trimmed) {
		return nil, false
	}
	if isTranscriptReplay(trimmed) {
		human := extractHumanLines(trimmed)
		if len(human) == 0 {
			return nil, false
		}
		return human, true
	}
	return []string{trimmed}, true
}
