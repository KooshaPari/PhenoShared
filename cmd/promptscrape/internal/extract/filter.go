package extract

import (
	"regexp"
	"strings"
)

// injectedPrefixes are harness-injected blocks without a closing tag.
//
// Tagged blocks are handled by injectedBlockTags, which strips them from
// wherever they appear; these have no boundary to find, so a message that
// starts with one is dropped whole.
var injectedPrefixes = []string{
	"# AGENTS.md",
}

// continuationPrefixes mark messages the harness generated to continue a turn.
var continuationPrefixes = []string{
	"<|",
	"<turn_aborted>",
	"<user_inst>",
}

// injectedBlockTags are harness-injected blocks that can appear *anywhere* in a
// user turn, not just at the start.
//
// The common shape is a genuine human prompt with a system reminder appended to
// it. Treating the whole message as injected would lose the prompt, and keeping
// the block verbatim pollutes a curation timeline, so the block is cut out and
// the surrounding text is kept.
var injectedBlockTags = []string{
	"system-reminder",
	"environment_context",
	"permissions instructions",
	"user_instructions",
	"agents_md",
	"project_context",
	"environment",
}

// harnessNoticePrefixes are messages the harness authored on the user's behalf.
//
// None of these were typed by a human. They reach the session store as user
// turns because the harness delivers its own instructions through the same
// channel, and they are the dominant source of noise in long-lived sessions:
// auto-continuation prompts, tool-media placeholders, background-task notices,
// swarm notifications and safety-review prompts.
var harnessNoticePrefixes = []string{
	"[auto]",
	"[System reminder:",
	"[Attached image associated with the preceding tool result:",
	"[Older tool screenshot omitted from history",
	"🐝 **Swarm await finished**",
	"**Background task**",
	"Reassess the user's request using its full context",
	"Review the request again and distinguish",
	"Perform one final, independent policy check",
}

// harnessNoticePatterns catch harness notices whose text varies per instance.
var harnessNoticePatterns = []*regexp.Regexp{
	// "You have 8 incomplete todos. Continue working, or update the todo tool."
	regexp.MustCompile(`^You have \d+ incomplete todos?\.`),
	// "turn 0 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" synthetic probe filler
	regexp.MustCompile(`^turn \d+ x{8,}\s*$`),
}

// nullPlaceholders are how a null prompt gets serialised into the transcript.
//
// A subagent spawned with no prompt stores the literal text "null" followed by
// the injected system reminder. Neither part is human input.
var nullPlaceholders = []string{"null", "none", "undefined"}

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

// isHarnessNotice reports whether text is a message the harness wrote on the
// user's behalf, such as an auto-continuation prompt or a tool-media placeholder.
func isHarnessNotice(text string) bool {
	trimmed := strings.TrimSpace(text)
	for _, p := range harnessNoticePrefixes {
		if strings.HasPrefix(trimmed, p) {
			return true
		}
	}
	for _, re := range harnessNoticePatterns {
		if re.MatchString(trimmed) {
			return true
		}
	}
	return false
}

// stripHarnessNoticeLines removes harness-notice lines from anywhere in text.
//
// isHarnessNotice only classifies a message by its first line, which is wrong
// for the very common shape where the harness appends its own notice *after* a
// genuine human prompt. The session store then holds one user message like:
//
//	go
//
//	You have 4 incomplete todos. Continue working, or update the todo tool.
//
// The human wrote "go"; the todo nudge is harness text. Keeping the whole block
// would both pollute the timeline and inflate any count taken over it, so the
// notice lines are cut and what remains is the human's own input.
//
// A line is only removed when it independently matches a harness notice pattern,
// so a genuine short prompt such as "go", ".", or "do it all" survives intact.
func stripHarnessNoticeLines(text string) (string, bool) {
	if !strings.Contains(text, "\n") {
		return text, false
	}
	lines := strings.Split(text, "\n")
	kept := make([]string, 0, len(lines))
	removed := false
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" && (isHarnessNotice(trimmed) || isContinuation(trimmed)) {
			removed = true
			continue
		}
		kept = append(kept, line)
	}
	if !removed {
		return text, false
	}
	return strings.Join(kept, "\n"), true
}

// isNullPlaceholder reports whether text is only a serialised null value.
func isNullPlaceholder(text string) bool {
	trimmed := strings.ToLower(strings.TrimSpace(text))
	for _, p := range nullPlaceholders {
		if trimmed == p {
			return true
		}
	}
	return false
}

// stripInjectedBlocks removes harness-injected blocks from anywhere in text.
//
// It returns the remaining text and whether anything was removed. An unclosed
// block is treated as running to the end of the message, because a truncated
// reminder is still harness text rather than human input.
func stripInjectedBlocks(text string) (string, bool) {
	remaining := text
	removed := false
	for _, tag := range injectedBlockTags {
		open := "<" + tag + ">"
		closeTag := "</" + tag + ">"
		for {
			start := strings.Index(remaining, open)
			if start < 0 {
				break
			}
			end := strings.Index(remaining[start:], closeTag)
			if end < 0 {
				remaining = remaining[:start]
				removed = true
				break
			}
			remaining = remaining[:start] + remaining[start+end+len(closeTag):]
			removed = true
		}
	}
	return remaining, removed
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
//   - Harness notices (auto-continuations, tool-media placeholders, background
//     task and swarm notifications, safety-review prompts) are dropped.
//   - Injected blocks embedded in an otherwise human message are cut out; if
//     nothing but a null placeholder is left, the message is dropped.
//   - A rendered transcript is reduced to the human's own input lines; if it has
//     none, it is dropped entirely.
//   - Anything else is kept verbatim as a single prompt.
func normalizePrompt(text string) ([]string, bool) {
	trimmed := strings.TrimSpace(text)
	if trimmed == "" {
		return nil, false
	}
	if isInjected(trimmed) || isContinuation(trimmed) || isHarnessNotice(trimmed) {
		return nil, false
	}

	cleaned, hadInjected := stripInjectedBlocks(trimmed)
	if hadInjected {
		cleaned = strings.TrimSpace(cleaned)
		if cleaned == "" || isNullPlaceholder(cleaned) || isHarnessNotice(cleaned) {
			return nil, false
		}
	}

	// A harness notice appended to a genuine prompt arrives as trailing lines of
	// the same user message, so it survives the prefix checks above. Cut those
	// lines and keep the human's own text. If nothing human remains, drop it.
	if stripped, hadNotices := stripHarnessNoticeLines(cleaned); hadNotices {
		cleaned = strings.TrimSpace(stripped)
		if cleaned == "" || isNullPlaceholder(cleaned) || isHarnessNotice(cleaned) {
			return nil, false
		}
	}

	if isTranscriptReplay(cleaned) {
		human := extractHumanLines(cleaned)
		if len(human) == 0 {
			return nil, false
		}
		return human, true
	}
	return []string{cleaned}, true
}
