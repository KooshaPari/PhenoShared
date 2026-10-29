package extract

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

// journalLine renders one journal entry as the JSON line the harness writes.
// testLine marshals v inline so a malformed line can also be appended verbatim.
func testLine(t *testing.T, v any) string {
	t.Helper()
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatalf("marshal journal entry: %v", err)
	}
	return string(b) + "\n"
}

// TestMergeJCodeJournalFeedsOnlyAppendedMessages pins the invariant that the
// journal contributes exactly the messages it appends: meta-only entries add
// nothing, malformed lines are skipped, and every appended message reaches the
// callback in file order.
func TestMergeJCodeJournalFeedsOnlyAppendedMessages(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "session_test.journal.jsonl")

	first := jcodeMessage{
		ID:        "message_1",
		Role:      "user",
		Timestamp: "2026-01-01T00:00:00.000001Z",
		Content:   []jcodeContentBlk{{Type: "text", Text: "first prompt"}},
	}
	second := jcodeMessage{
		ID:        "message_2",
		Role:      "assistant",
		Timestamp: "2026-01-01T00:00:01.000001Z",
		Content:   []jcodeContentBlk{{Type: "text", Text: "first answer"}},
	}

	body := testLine(t, jcodeJournalEntry{AppendMessages: []jcodeMessage{first, second}}) +
		testLine(t, jcodeJournalEntry{Meta: &jcodeJournalMeta{WorkingDir: "/tmp", Status: "active"}}) +
		"{not valid json at all\n"

	if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
		t.Fatalf("write journal: %v", err)
	}

	var got []jcodeMessage
	err := mergeJCodeJournal(path, func(m jcodeMessage) { got = append(got, m) })
	if err != nil {
		t.Fatalf("mergeJCodeJournal returned error: %v", err)
	}

	want := []jcodeMessage{first, second}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("callback received %#v, want %#v", got, want)
	}
}

// TestMergeJCodeJournalMissingFileIsNotAnError pins the invariant that a session
// which only has a snapshot (no journal yet) still extracts cleanly.
func TestMergeJCodeJournalMissingFileIsNotAnError(t *testing.T) {
	path := filepath.Join(t.TempDir(), "does-not-exist.journal.jsonl")

	called := false
	if err := mergeJCodeJournal(path, func(jcodeMessage) { called = true }); err != nil {
		t.Fatalf("mergeJCodeJournal on missing file returned error: %v", err)
	}
	if called {
		t.Fatal("callback ran for a missing journal")
	}
}

// TestMergeJCodeJournalSkipsBlankAndInvalidLines pins the invariant that a
// partially-written journal (blank line, garbage line) does not abort the merge
// and does not inject phantom messages.
func TestMergeJCodeJournalSkipsBlankAndInvalidLines(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "partial.journal.jsonl")

	good := jcodeMessage{
		ID:        "message_good",
		Role:      "user",
		Timestamp: "2026-01-02T00:00:00.000001Z",
		Content:   []jcodeContentBlk{{Type: "text", Text: "real prompt"}},
	}

	body := "\n" + "   \n" + `{"append_messages":[]}` + "\n" +
		testLine(t, jcodeJournalEntry{AppendMessages: []jcodeMessage{good}}) +
		`{"append_messages":[{"id":` + "\n"

	if err := os.WriteFile(path, []byte(body), 0o600); err != nil {
		t.Fatalf("write journal: %v", err)
	}

	var got []jcodeMessage
	if err := mergeJCodeJournal(path, func(m jcodeMessage) { got = append(got, m) }); err != nil {
		t.Fatalf("mergeJCodeJournal returned error: %v", err)
	}
	want := []jcodeMessage{good}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("callback received %#v, want %#v", got, want)
	}
}

// TestJCodeUserTextPicksHumanTextBlock pins the invariant that only the first
// non-empty "text" block counts as human input. Tool results share the user
// role but are never prompts, so a message made only of tool output yields "".
func TestJCodeUserTextPicksHumanTextBlock(t *testing.T) {
	tests := []struct {
		name string
		msg  jcodeMessage
		want string
	}{
		{
			name: "text block before tool result",
			msg: jcodeMessage{Content: []jcodeContentBlk{
				{Type: "text", Text: "why did the build fail"},
				{Type: "tool_result", Text: "exit status 1"},
			}},
			want: "why did the build fail",
		},
		{
			name: "tool result then text block",
			msg: jcodeMessage{Content: []jcodeContentBlk{
				{Type: "tool_result", Text: "exit status 1"},
				{Type: "text", Text: "and now fix it"},
			}},
			want: "and now fix it",
		},
		{
			name: "only tool result",
			msg: jcodeMessage{Content: []jcodeContentBlk{
				{Type: "tool_result", Text: "exit status 1"},
			}},
			want: "",
		},
		{
			name: "empty text block",
			msg: jcodeMessage{Content: []jcodeContentBlk{
				{Type: "text", Text: ""},
			}},
			want: "",
		},
		{
			name: "whitespace-only text block",
			msg: jcodeMessage{Content: []jcodeContentBlk{
				{Type: "text", Text: "   \n\t "},
			}},
			want: "",
		},
		{
			name: "no content blocks",
			msg:  jcodeMessage{},
			want: "",
		},
		{
			name: "text block is trimmed",
			msg: jcodeMessage{Content: []jcodeContentBlk{
				{Type: "text", Text: "  explain the diff  "},
			}},
			want: "explain the diff",
		},
		{
			name: "first non-empty text block wins",
			msg: jcodeMessage{Content: []jcodeContentBlk{
				{Type: "text", Text: "first"},
				{Type: "text", Text: "second"},
			}},
			want: "first",
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := jcodeUserText(tc.msg); got != tc.want {
				t.Fatalf("jcodeUserText = %q, want %q", got, tc.want)
			}
		})
	}
}

// TestJCodePromptIDSequenceSuffix pins the invariant that a message holding a
// single prompt keeps the raw message id (so ids stay traceable to the source),
// while a message holding several prompts gets 1-based, unique suffixes.
func TestJCodePromptIDSequenceSuffix(t *testing.T) {
	tests := []struct {
		name  string
		id    string
		index int
		total int
		want  string
	}{
		{name: "zero prompts keeps id", id: "message_1", index: 0, total: 0, want: "message_1"},
		{name: "single prompt keeps id", id: "message_1", index: 0, total: 1, want: "message_1"},
		{name: "first of three", id: "message_1", index: 0, total: 3, want: "message_1#1"},
		{name: "middle of three", id: "message_1", index: 1, total: 3, want: "message_1#2"},
		{name: "last of three", id: "message_1", index: 2, total: 3, want: "message_1#3"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := jcodePromptID(tc.id, tc.index, tc.total); got != tc.want {
				t.Fatalf("jcodePromptID(%q, %d, %d) = %q, want %q",
					tc.id, tc.index, tc.total, got, tc.want)
			}
		})
	}
}

// TestJCodePromptIDUniqueness pins the invariant that the prompts split out of
// one message never collide, which is what makes the extracted timeline
// stable and de-duplicable across re-runs.
func TestJCodePromptIDUniqueness(t *testing.T) {
	const id = "message_1793249328054_4234567178120536763"
	const total = 5

	seen := make(map[string]bool, total)
	for i := 0; i < total; i++ {
		got := jcodePromptID(id, i, total)
		if seen[got] {
			t.Fatalf("jcodePromptID produced duplicate id %q at index %d", got, i)
		}
		seen[got] = true
	}
	if len(seen) != total {
		t.Fatalf("got %d unique ids, want %d", len(seen), total)
	}
}
