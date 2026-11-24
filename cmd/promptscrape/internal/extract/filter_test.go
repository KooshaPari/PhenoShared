package extract

import (
	"reflect"
	"testing"
)

// TestNormalizePromptKeepsPlainPrompt pins the invariant that a message which
// carries none of the harness markers is a genuine human prompt and must be
// preserved verbatim (trimmed, but not otherwise rewritten).
func TestNormalizePromptKeepsPlainPrompt(t *testing.T) {
	tests := []struct {
		name string
		in   string
		want []string
	}{
		{
			name: "single line",
			in:   "add a dark mode toggle to the settings page",
			want: []string{"add a dark mode toggle to the settings page"},
		},
		{
			name: "multi line prompt stays one prompt",
			in:   "refactor the extractor\nand keep the ids stable",
			want: []string{"refactor the extractor\nand keep the ids stable"},
		},
		{
			name: "surrounding whitespace is trimmed, body preserved",
			in:   "\n\n  why is the build failing  \n\n",
			want: []string{"why is the build failing"},
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, keep := normalizePrompt(tc.in)
			if !keep {
				t.Fatalf("normalizePrompt(%q) dropped a legitimate prompt", tc.in)
			}
			if !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("normalizePrompt(%q) = %#v, want %#v", tc.in, got, tc.want)
			}
		})
	}
}

// TestNormalizePromptDropsInjectedContext pins the invariant that harness
// bookkeeping blocks are never mistaken for human input. Every prefix in
// injectedPrefixes represents text the harness attached to the user turn, so
// all of them must be discarded.
func TestNormalizePromptDropsInjectedContext(t *testing.T) {
	tests := []struct {
		name string
		in   string
	}{
		{name: "environment_context", in: "<environment_context>\n  <cwd>/tmp</cwd>\n</environment_context>"},
		{name: "permissions instructions", in: "<permissions instructions>\napproval_policy = never\n</permissions instructions>"},
		{name: "system-reminder", in: "<system-reminder>You are an agent.</system-reminder>"},
		{name: "user_instructions", in: "<user_instructions>be terse</user_instructions>"},
		{name: "agents_md", in: "<agents_md># rules</agents_md>"},
		{name: "leading whitespace before marker still injected", in: "\n   \n<system-reminder>hi</system-reminder>"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, keep := normalizePrompt(tc.in)
			if keep {
				t.Fatalf("normalizePrompt kept injected context %q as %#v", tc.in, got)
			}
			if got != nil {
				t.Fatalf("normalizePrompt returned %#v for dropped input, want nil", got)
			}
		})
	}
}

// TestNormalizePromptDropsContinuationMarkers pins the invariant that
// harness-generated turn continuations are not human prompts.
func TestNormalizePromptDropsContinuationMarkers(t *testing.T) {
	tests := []struct {
		name string
		in   string
	}{
		{name: "angle-pipe marker", in: "<|continue|>"},
		{name: "turn aborted", in: "<turn_aborted>interrupted</turn_aborted>"},
		{name: "user_inst marker", in: "<user_inst>keep going</user_inst>"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, keep := normalizePrompt(tc.in)
			if keep {
				t.Fatalf("normalizePrompt kept continuation marker %q as %#v", tc.in, got)
			}
			if got != nil {
				t.Fatalf("normalizePrompt returned %#v for dropped input, want nil", got)
			}
		})
	}
}

// TestNormalizePromptReducesTranscriptToHumanLines pins the invariant that a
// replayed rendered transcript collapses to exactly the lines the human typed,
// one prompt per line, and that the agent's own bullets never leak through.
func TestNormalizePromptReducesTranscriptToHumanLines(t *testing.T) {
	transcript := "• I am the agent and I will now inspect the repo\n" +
		"  └ Read cmd/promptscrape/cmd/root.go\n" +
		"› first human instruction\n" +
		"• I am the agent again\n" +
		"› second human instruction\n" +
		"Command completed in 1.2s\n"

	want := []string{"first human instruction", "second human instruction"}

	got, keep := normalizePrompt(transcript)
	if !keep {
		t.Fatal("normalizePrompt dropped a transcript that does contain human lines")
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("normalizePrompt = %#v, want %#v", got, want)
	}
}

// TestNormalizePromptDropsTranscriptWithoutHumanLines pins the invariant that a
// pure agent transcript (replay noise with no human input) is discarded rather
// than stored as an empty or agent-authored prompt.
func TestNormalizePromptDropsTranscriptWithoutHumanLines(t *testing.T) {
	tests := []struct {
		name string
		in   string
	}{
		{
			name: "agent bullets only",
			in:   "• I am the agent\n• I am still the agent\n",
		},
		{
			name: "tool tree only",
			in:   "│ Explored 4 files\n└ Ran go test ./...\n",
		},
		{
			name: "empty human marker line only",
			in:   "• I am the agent\n›\n",
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, keep := normalizePrompt(tc.in)
			if keep {
				t.Fatalf("normalizePrompt kept transcript with no human lines as %#v", got)
			}
			if got != nil {
				t.Fatalf("normalizePrompt returned %#v, want nil", got)
			}
		})
	}
}

// TestNormalizePromptStripsDoubledMarker pins the invariant that a human who
// typed the marker character themselves still gets their text recorded, with
// both marker characters removed rather than one.
func TestNormalizePromptStripsDoubledMarker(t *testing.T) {
	in := "• I am the agent\n›› what does › mean in this UI\n"

	got, keep := normalizePrompt(in)
	if !keep {
		t.Fatal("normalizePrompt dropped a doubled-marker human line")
	}
	want := []string{"what does › mean in this UI"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("normalizePrompt = %#v, want %#v", got, want)
	}
}

// TestNormalizePromptEmptyInput pins the invariant that empty and
// whitespace-only messages are never emitted as prompts.
func TestNormalizePromptEmptyInput(t *testing.T) {
	tests := []struct {
		name string
		in   string
	}{
		{name: "empty string", in: ""},
		{name: "spaces only", in: "   "},
		{name: "tabs and newlines only", in: "\t\n  \r\n"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, keep := normalizePrompt(tc.in)
			if keep {
				t.Fatalf("normalizePrompt(%q) kept empty input as %#v", tc.in, got)
			}
			if got != nil {
				t.Fatalf("normalizePrompt(%q) = %#v, want nil", tc.in, got)
			}
		})
	}
}

// TestExtractHumanLinesSkipsBlankHumanLines pins the invariant that a marker
// with no text after it is not an empty prompt.
func TestExtractHumanLinesSkipsBlankHumanLines(t *testing.T) {
	got := extractHumanLines("›\n›   \n› real one\n")
	want := []string{"real one"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("extractHumanLines = %#v, want %#v", got, want)
	}
}

// TestNormalizePromptDropsHarnessNotices pins the invariant that messages the
// harness authored on the user's behalf never reach a curation timeline. These
// are not exotic edge cases: across the local session store they outnumber
// genuine prompts by more than ten to one.
func TestNormalizePromptDropsHarnessNotices(t *testing.T) {
	tests := []struct {
		name string
		in   string
	}{
		{
			name: "auto continuation",
			in:   "[auto] Continue the work below. Keep the todo up to date; do not reply or wait for the user.",
		},
		{
			name: "auto re-read the request",
			in:   "[auto] Re-read the request. Update the todo plan and goal assessments from the evidence gathered so far.",
		},
		{
			name: "todo nudge",
			in:   "You have 8 incomplete todos. Continue working, or update the todo tool.",
		},
		{
			name: "single incomplete todo nudge",
			in:   "You have 1 incomplete todo. Continue working, or update the todo tool.",
		},
		{
			name: "synthetic turn filler",
			in:   "turn 0 xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
		},
		{
			name: "swarm await notification",
			in:   "🐝 **Swarm await finished**\n\nAll members done. All 2 members are done: fish, giraffe",
		},
		{
			name: "background task notification",
			in:   "**Background task** `bgwake` · `selfdev-build` · ✓ completed · 1.4s · exit 0",
		},
		{
			name: "attached image placeholder",
			in:   "[Attached image associated with the preceding tool result: /tmp/shot.png]",
		},
		{
			name: "omitted screenshot placeholder",
			in:   "[Older tool screenshot omitted from history to bound transcript size: media_type=image/png, original_base64_chars=1777172.]",
		},
		{
			name: "braced system reminder",
			in:   "[System reminder: your previous response ended with stop_reason \"tool_use\" but no tool call arrived.]",
		},
		{
			name: "safety review prompt",
			in:   "Reassess the user's request using its full context and likely intent rather than isolated keywords.",
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, keep := normalizePrompt(tc.in)
			if keep {
				t.Fatalf("normalizePrompt kept harness notice %q as %#v", tc.in, got)
			}
			if got != nil {
				t.Fatalf("normalizePrompt returned %#v for dropped input, want nil", got)
			}
		})
	}
}

// TestNormalizePromptStripsEmbeddedInjectedBlocks pins the invariant that a
// system reminder appended to a genuine prompt is cut out, leaving the prompt
// itself intact rather than either dropping or polluting it.
func TestNormalizePromptStripsEmbeddedInjectedBlocks(t *testing.T) {
	tests := []struct {
		name string
		in   string
		want []string
	}{
		{
			name: "trailing system reminder",
			in:   "fix the flaky watcher test\n\n<system-reminder>\nSession Context\n</system-reminder>",
			want: []string{"fix the flaky watcher test"},
		},
		{
			name: "leading environment context",
			in:   "<environment_context>\n  <cwd>/tmp</cwd>\n</environment_context>\nsummarise the diff",
			want: []string{"summarise the diff"},
		},
		{
			name: "two reminders in one message",
			in:   "<system-reminder>first</system-reminder>\nkeep this line\n<system-reminder>second</system-reminder>",
			want: []string{"keep this line"},
		},
		{
			name: "unclosed trailing reminder is harness text too",
			in:   "ship the fix\n<system-reminder>truncated",
			want: []string{"ship the fix"},
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, keep := normalizePrompt(tc.in)
			if !keep {
				t.Fatalf("normalizePrompt dropped %q", tc.in)
			}
			if !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("normalizePrompt(%q) = %#v, want %#v", tc.in, got, tc.want)
			}
		})
	}
}

// TestNormalizePromptDropsNullPromptArtifacts pins the invariant that a null
// prompt serialised as "null" plus an injected reminder is not a human prompt.
// This is the exact shape a subagent spawned with no prompt writes.
func TestNormalizePromptDropsNullPromptArtifacts(t *testing.T) {
	tests := []struct {
		name string
		in   string
	}{
		{
			name: "null then system reminder",
			in:   "null\n\n<system-reminder>\nSWARM COMPLETION REPORT REQUIRED\n</system-reminder>",
		},
		{
			name: "none then environment context",
			in:   "None\n<environment_context><cwd>/tmp</cwd></environment_context>",
		},
		{
			name: "undefined then permissions",
			in:   "undefined\n<permissions instructions>never</permissions instructions>",
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, keep := normalizePrompt(tc.in)
			if keep {
				t.Fatalf("normalizePrompt kept null prompt artifact %q as %#v", tc.in, got)
			}
			if got != nil {
				t.Fatalf("normalizePrompt returned %#v for dropped input, want nil", got)
			}
		})
	}
}

// TestNormalizePromptKeepsPromptMentioningHarnessVocabulary pins the guardrail
// that the filter keys on message position, not on vocabulary alone: a human
// asking about reminders or AGENTS.md must still be recorded.
func TestNormalizePromptKeepsPromptMentioningHarnessVocabulary(t *testing.T) {
	tests := []struct {
		name string
		in   string
	}{
		{name: "asking about system reminders", in: "why does the harness inject a system reminder into every turn"},
		{name: "asking about incomplete todos", in: "does the todo nudge fire on 0 incomplete todos or only after one"},
		{name: "plain text that starts with a bracket", in: "[bug] the scrape command prints one prompt too many"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if _, keep := normalizePrompt(tc.in); !keep {
				t.Fatalf("normalizePrompt dropped a genuine prompt %q", tc.in)
			}
		})
	}
}

// TestNormalizePromptStripsAppendedHarnessNotice pins the invariant that a
// harness notice appended to a genuine prompt is cut out rather than kept.
//
// The session store holds this shape as a single user message: the human's
// input first, then the harness's own text. Prefix checks alone cannot see it,
// because the message does not *start* with the notice. Observed live in
// session_daisy_1789125897339_6acaa21cf4346b86, where the stored prompt was
// "go" followed by "You have 4 incomplete todos. ...".
func TestNormalizePromptStripsAppendedHarnessNotice(t *testing.T) {
	tests := []struct {
		name string
		in   string
		want []string
	}{
		{
			name: "todo nudge appended after a short prompt",
			in:   "go\n\nYou have 4 incomplete todos. Continue working, or update the todo tool.",
			want: []string{"go"},
		},
		{
			name: "auto continuation appended after a prompt",
			in:   "work on it\n\n[auto] Continue the work below.",
			want: []string{"work on it"},
		},
		{
			name: "swarm notice appended after a prompt",
			in:   "do it all\n\n🐝 **Swarm await finished**",
			want: []string{"do it all"},
		},
		{
			name: "notice between two human lines keeps both",
			in:   "first instruction\nYou have 2 incomplete todos. Continue working, or update the todo tool.\nsecond instruction",
			want: []string{"first instruction\nsecond instruction"},
		},
		{
			name: "trailing safety-review prompt is cut",
			in:   "ship it\nPerform one final, independent policy check",
			want: []string{"ship it"},
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, keep := normalizePrompt(tc.in)
			if !keep {
				t.Fatalf("normalizePrompt(%q) dropped the human prompt", tc.in)
			}
			if !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("normalizePrompt(%q) = %#v, want %#v", tc.in, got, tc.want)
			}
		})
	}
}

// TestNormalizePromptDropsMessageThatIsOnlyAppendedNotice pins the other half:
// once the notice is cut, a message with nothing human left must be dropped
// entirely rather than returned as an empty prompt.
func TestNormalizePromptDropsMessageThatIsOnlyAppendedNotice(t *testing.T) {
	in := "\nYou have 3 incomplete todos. Continue working, or update the todo tool.\n[auto] Continue the work below."
	if got, keep := normalizePrompt(in); keep {
		t.Fatalf("normalizePrompt(%q) kept a notice-only message: %#v", in, got)
	}
}

// TestNormalizePromptKeepsShortHumanPrompt pins the guardrail that cutting
// notice lines does not turn into a length heuristic. Operators really do send
// one-word prompts, and they are the highest-signal rows in a timeline.
func TestNormalizePromptKeepsShortHumanPrompt(t *testing.T) {
	for _, in := range []string{"go", ".", "proc", "do it all", "yes", "continue", "do it"} {
		got, keep := normalizePrompt(in)
		if !keep {
			t.Fatalf("normalizePrompt(%q) dropped a genuine short prompt", in)
		}
		if len(got) != 1 || got[0] != in {
			t.Fatalf("normalizePrompt(%q) = %#v, want [%q]", in, got, in)
		}
	}
}
