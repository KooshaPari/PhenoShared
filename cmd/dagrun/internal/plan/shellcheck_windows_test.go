//go:build windows

package plan

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// A `cmd:` work set is written against POSIX tools. On Windows the same names
// exist as different programs, and System32\find.exe exits 0 while printing
// nothing, so a broken environment looks like a plan with no work. The preflight
// must refuse that loudly instead of returning an empty unit list.
func TestPreflightDiscoveryRefusesWithoutAShell(t *testing.T) {
	empty := t.TempDir()
	t.Setenv("PATH", empty)

	err := preflightDiscovery("find . -name '*.go'")
	if err == nil {
		t.Fatal("a cmd: source with no sh on PATH was accepted; it would return zero units silently")
	}
	msg := err.Error()
	if !strings.Contains(msg, "POSIX shell") {
		t.Errorf("error should say a POSIX shell is needed, got %q", msg)
	}
	if !strings.Contains(msg, "System32") {
		t.Errorf("error should name the PATH fix, got %q", msg)
	}
}

// The classification only matters for the directory Windows' own tools live in,
// so it must not claim an arbitrary path is a System32 binary.
func TestIsSystem32Binary(t *testing.T) {
	root := os.Getenv("SystemRoot")
	if root == "" {
		root = `C:\Windows`
	}
	inside := filepath.Join(root, "System32", "find.exe")
	if !isSystem32Binary(inside) {
		t.Errorf("%s should be classified as a System32 binary", inside)
	}
	outside := filepath.Join(t.TempDir(), "find.exe")
	if isSystem32Binary(outside) {
		t.Errorf("%s should not be classified as a System32 binary", outside)
	}
}

// Whole-word matching keeps "findings" from being read as the `find` tool.
func TestMentionsToolMatchesWholeWords(t *testing.T) {
	if !mentionsTool("find . -name '*.go'", "find") {
		t.Error("a real find invocation was not detected")
	}
	if mentionsTool("write the findings to disk", "find") {
		t.Error("the word findings was mistaken for the find tool")
	}
	if !mentionsTool("git ls-files | sed 's|^./||'", "sed") {
		t.Error("a piped sed invocation was not detected")
	}
}
