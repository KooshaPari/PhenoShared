package resolve

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"
)

const (
	// testJCodeID is a well-formed JCode session id: session_<lane>_<13 digits>_<16 hex>.
	testJCodeID = "session_pig_1792638703385_34d0c212ece1d6b9"
	// testCodexID is a well-formed Codex thread id (a lowercase UUID).
	testCodexID = "01a11ecd-9cb0-7003-acd4-2fa6e255169e"
)

// TestFromContentFindsJCodeSessionID pins the invariant that a JCode session id
// embedded in a state HTML is detected.
func TestFromContentFindsJCodeSessionID(t *testing.T) {
	html := `<html><body><a href="/sessions/` + testJCodeID + `">open</a></body></html>`

	got := FromContent(html)
	want := []string{testJCodeID}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("FromContent = %#v, want %#v", got, want)
	}
}

// TestFromContentFindsCodexUUID pins the invariant that a Codex thread id
// embedded in a state HTML is detected.
func TestFromContentFindsCodexUUID(t *testing.T) {
	html := `<div data-thread="` + testCodexID + `">codex lane</div>`

	got := FromContent(html)
	want := []string{testCodexID}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("FromContent = %#v, want %#v", got, want)
	}
}

// TestFromContentOrdersJCodeBeforeCodexOnTie pins the invariant that when a file
// references a JCode lane and a Codex thread equally often, the JCode session is
// offered first: the JCode lane is the session being audited, the Codex thread
// is context it referenced.
func TestFromContentOrdersJCodeBeforeCodexOnTie(t *testing.T) {
	html := "<h1>audit</h1>\n" +
		`<span>` + testCodexID + `</span>` + "\n" +
		`<span>` + testJCodeID + `</span>` + "\n"

	got := FromContent(html)
	want := []string{testJCodeID, testCodexID}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("FromContent = %#v, want %#v (JCode first)", got, want)
	}
}

// TestFromContentDeduplicatesRepeatedID pins the invariant that an id mentioned
// many times is returned once, so callers never see the same candidate twice.
func TestFromContentDeduplicatesRepeatedID(t *testing.T) {
	html := `<a href="/s/` + testJCodeID + `">` + testJCodeID + `</a>` +
		`<a href="/s/` + testJCodeID + `">` + testJCodeID + `</a>`

	got := FromContent(html)
	want := []string{testJCodeID}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("FromContent = %#v, want %#v (deduplicated)", got, want)
	}
}

// TestFromContentNoIDReturnsEmpty pins the invariant that HTML with no session
// reference yields no candidates rather than an error or a bogus id.
func TestFromContentNoIDReturnsEmpty(t *testing.T) {
	tests := []struct {
		name string
		html string
	}{
		{name: "plain text", html: "<html><body>nothing here</body></html>"},
		{name: "empty document", html: ""},
		{name: "near miss lane prefix", html: "session_PIG_1792638703385_34d0c212ece1d6b9"},
		{name: "near miss short suffix", html: "session_pig_1792638703385_34d0c212"},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			if got := FromContent(tc.html); len(got) != 0 {
				t.Fatalf("FromContent(%q) = %#v, want no candidates", tc.html, got)
			}
		})
	}
}

// TestFromContentRanksByFrequency pins the invariant that the caller's first
// candidate is the session referenced most often, which is the one the page is
// actually about.
func TestFromContentRanksByFrequency(t *testing.T) {
	// The rare id appears first in the document, so only frequency ordering can
	// put the frequent one ahead of it.
	html := `<span>` + testCodexID + `</span>`
	for i := 0; i < 5; i++ {
		html += `<a href="/s/` + testJCodeID + `">` + testJCodeID + `</a>`
	}

	got := FromContent(html)
	want := []string{testJCodeID, testCodexID}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("FromContent = %#v, want %#v (most frequent first)", got, want)
	}
}

// TestFromHTMLReadsFileAndDelegates pins the invariant that the file-based
// entrypoint applies the same extraction as the string-based one.
func TestFromHTMLReadsFileAndDelegates(t *testing.T) {
	path := filepath.Join(t.TempDir(), "state.html")
	html := `<a href="/s/` + testJCodeID + `">state</a>`
	if err := os.WriteFile(path, []byte(html), 0o600); err != nil {
		t.Fatalf("write html: %v", err)
	}

	got, err := FromHTML(path)
	if err != nil {
		t.Fatalf("FromHTML returned error: %v", err)
	}
	want := []string{testJCodeID}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("FromHTML = %#v, want %#v", got, want)
	}
}

// TestFromHTMLMissingFileErrors pins the invariant that a bad path surfaces as
// an error instead of silently returning no candidates.
func TestFromHTMLMissingFileErrors(t *testing.T) {
	path := filepath.Join(t.TempDir(), "nope.html")
	if _, err := FromHTML(path); err == nil {
		t.Fatal("FromHTML on a missing file returned nil error")
	}
}

// TestCurrentPrefersExplicitEnv pins the invariant that JCODE_SESSION_ID wins
// over any on-disk discovery, so a caller pinned to a session cannot drift to a
// different one. This branch never touches the real ~/.jcode.
func TestCurrentPrefersExplicitEnv(t *testing.T) {
	const pinned = "session_pig_1792638703385_34d0c212ece1d6b9"
	t.Setenv("JCODE_SESSION_ID", "  "+pinned+"  ")

	got, err := Current()
	if err != nil {
		t.Fatalf("Current returned error: %v", err)
	}
	if got != pinned {
		t.Fatalf("Current = %q, want %q (env value trimmed)", got, pinned)
	}
}
