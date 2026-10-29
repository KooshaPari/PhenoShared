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
