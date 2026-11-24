package harness

import "testing"

// These cases encode the parse contract: an id is only accepted when a
// recognised key names it, and the LAST naming object wins because that is the
// most recent view of the same session.
func TestParseSessionID(t *testing.T) {
	cases := []struct {
		name    string
		in      string
		wantID  string
		wantSrc string
	}{
		{
			name:    "jsonl last object wins",
			in:      `{"session_id":"old"}` + "\n" + `{"session_id":"new","type":"done"}` + "\n",
			wantID:  "new",
			wantSrc: "stdout:session_id",
		},
		{
			name:    "camel case key",
			in:      `{"sessionId":"abc-123"}` + "\n",
			wantID:  "abc-123",
			wantSrc: "stdout:sessionId",
		},
		{
			name:    "codex thread id",
			in:      `{"thread_id":"019a2f"}` + "\n",
			wantID:  "019a2f",
			wantSrc: "stdout:thread_id",
		},
		{
			name:    "single object without newline",
			in:      `{"conversation_id":"c1"}`,
			wantID:  "c1",
			wantSrc: "stdout:conversation_id",
		},
		{
			// A bare "id" names artifacts, spans and nodes in real output.
			// Reading it as a session would fabricate identity.
			name: "bare id is not a session",
			in:   `{"id":"node-1"}` + "\n",
		},
		{
			name: "path-like value rejected",
			in:   `{"session_id":"/Users/someone/.jcode/sessions/x"}` + "\n",
		},
		{
			name: "embedded whitespace rejected",
			in:   `{"session_id":"two words"}` + "\n",
		},
		{
			name: "empty value rejected",
			in:   `{"session_id":""}` + "\n",
		},
		{
			name: "non-json text ignored",
			in:   "session_id: nope\nnothing here\n",
		},
		{
			name: "empty input",
			in:   "",
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			id, src := ParseSessionID([]byte(c.in))
			if id != c.wantID || src != c.wantSrc {
				t.Fatalf("got (%q, %q), want (%q, %q)", id, src, c.wantID, c.wantSrc)
			}
		})
	}
}

// A malformed line must not abort the walk: harness output interleaves
// progress lines, warnings and blank lines with the JSON events.
func TestParseSessionIDSkipsMalformedLines(t *testing.T) {
	in := "warning: something\n{\"session_id\":\"keepme\"}\n{bad json}\n"
	id, _ := ParseSessionID([]byte(in))
	if id != "keepme" {
		t.Fatalf("got %q, want keepme", id)
	}
}
