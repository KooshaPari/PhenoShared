package mcp

import (
	"bytes"
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// goldenVersion is the build version the golden transcripts were recorded
// with.
//
// It is pinned here so the goldens stay valid when the build version changes.
// The goldens lock the wire format, not the version number.
const goldenVersion = "1.2.0"

// wantTools is the catalogue as it shipped before the HTTP transport existed.
//
// Nineteen tools, in the order the stdio transport advertises them. A new tool
// has to be added here deliberately, which is the point: the list is the
// contract a stdio client already depends on.
var wantTools = []string{
	"dagrun_next", "dagrun_claim", "dagrun_done", "dagrun_fail", "dagrun_skip",
	"dagrun_status", "dagrun_validate", "dagrun_plan", "dagrun_explain",
	"dagrun_trace", "dagrun_submit", "dagrun_run", "dagrun_query",
	"dagrun_recover", "dagrun_replan", "dagrun_stats", "dagrun_lint",
	"dagrun_doctor", "dagrun_export",
}

// serveBytes drives one session over a static request list and returns the
// exact bytes the server wrote.
//
// The bytes matter. The stdio transport is a compatibility surface: a client
// that spawns `dagrun mcp` must not see a single byte change because the
// server grew a second transport. Whitespace, key order and framing are all
// visible to that client.
func serveBytes(t *testing.T, lines []string, version string) []byte {
	t.Helper()
	in := strings.NewReader(strings.Join(lines, "\n") + "\n")
	var out bytes.Buffer
	srv := New(Config{Version: version})
	if err := srv.Serve(context.Background(), in, &out); err != nil {
		t.Fatalf("serve: %v", err)
	}
	return out.Bytes()
}

// TestStdioIsByteIdenticalToTheShippedServer locks the stdio wire format.
//
// The golden was recorded from the binary as it shipped before the HTTP
// transport existed. This compares bytes, not fields, because "the fields are
// the same" is not the compatibility promise: the promise is that the bytes
// are the same.
func TestStdioIsByteIdenticalToTheShippedServer(t *testing.T) {
	golden, err := os.ReadFile(filepath.Join("testdata", "stdio_golden.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	got := serveBytes(t, []string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"nope","arguments":{}}}`,
	}, goldenVersion)
	if !bytes.Equal(got, golden) {
		t.Errorf("the stdio wire format changed:\n--- got ---\n%s\n--- want ---\n%s", got, golden)
	}
}

// TestStdioToolCallIsByteIdenticalToTheShippedServer is the same promise for
// a real tool call: the framing of a successful tools/call must not move.
func TestStdioToolCallIsByteIdenticalToTheShippedServer(t *testing.T) {
	golden, err := os.ReadFile(filepath.Join("testdata", "stdio_status_golden.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	dir := installTestRun(t)

	wd, _ := os.Getwd()
	defer func() { _ = os.Chdir(wd) }()
	if err := os.Chdir(filepath.Dir(dir)); err != nil {
		t.Fatal(err)
	}

	got := serveBytes(t, []string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"dagrun_status","arguments":{}}}`,
	}, goldenVersion)
	frames := bytes.Split(bytes.TrimRight(got, "\n"), []byte("\n"))
	if len(frames) != 2 {
		t.Fatalf("got %d frames, want 2 (initialize and tools/call)", len(frames))
	}
	if want := bytes.TrimRight(golden, "\n"); !bytes.Equal(frames[1], want) {
		t.Errorf("the tools/call frame changed:\n--- got ---\n%s\n--- want ---\n%s", frames[1], want)
	}
}

// TestStdioAdvertisesTheShippedToolSet checks the catalogue by name.
//
// The golden above already pins the exact bytes; this states the same fact in
// a form a reader can check without a diff, and it fails with a message that
// names the tool that moved.
func TestStdioAdvertisesTheShippedToolSet(t *testing.T) {
	got := ToolNames()
	if len(got) != len(wantTools) {
		t.Fatalf("advertised %d tools, want %d", len(got), len(wantTools))
	}
	for i, name := range wantTools {
		if got[i] != name {
			t.Errorf("tool %d = %q, want %q", i, got[i], name)
		}
	}
}

// TestEveryAdvertisedToolHasExactlyOneHandler is the anti-duplication guard
// for the catalogue itself: a name may not be advertised twice, or two
// handlers would answer for it and the one a client reached would depend on
// map order.
func TestEveryAdvertisedToolHasExactlyOneHandler(t *testing.T) {
	seen := map[string]bool{}
	for _, spec := range toolSpecs() {
		if seen[spec.Name] {
			t.Errorf("tool %q is registered twice", spec.Name)
		}
		seen[spec.Name] = true
		if spec.call == nil {
			t.Errorf("tool %q has no handler", spec.Name)
		}
		if spec.InputSchema == nil {
			t.Errorf("tool %q has no input schema", spec.Name)
		}
	}
	if len(seen) != len(wantTools) {
		t.Errorf("the catalogue holds %d tools, want %d", len(seen), len(wantTools))
	}
}

// installTestRun writes a run directory and returns its path.
//
// It installs the same plan the stdio golden was recorded against, so a
// byte comparison of a tools/call result means something.
func installTestRun(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	p, err := plan.Parse([]byte(testPlan))
	if err != nil {
		t.Fatal(err)
	}
	p.Root = root
	dir := filepath.Join(root, ".dagrun")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), []byte(testPlan), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := store.Open(dir, p, []byte(testPlan), true); err != nil {
		t.Fatal(err)
	}
	return dir
}
