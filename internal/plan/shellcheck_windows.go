//go:build windows

package plan

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// posixTools are the commands a `cmd:` discovery script is written against.
//
// Windows ships several same-named programs that are not the POSIX ones:
// System32\find.exe searches text, it does not walk a directory tree, so
// `find . -name '*.go'` exits 0 and prints nothing. The run then looks like a
// plan with no work rather than a broken environment, which is the worst failure
// mode this tool has: the operator sees an empty work set and no error.
var posixTools = []string{
	"find", "sed", "grep", "awk", "xargs", "sort", "uniq",
	"head", "tail", "wc", "dirname", "basename", "cat", "cut", "tr",
}

// preflightDiscovery turns that silent zero into a loud, actionable error.
func preflightDiscovery(script string) error {
	if _, err := exec.LookPath("sh"); err != nil {
		return fmt.Errorf("cmd: discovery runs through `sh -c` and no POSIX shell was found on PATH; " +
			"install Git for Windows (or MSYS2/WSL) and put its usr\\bin ahead of %%SystemRoot%%\\System32")
	}

	var misrouted []string
	for _, tool := range posixTools {
		if !mentionsTool(script, tool) {
			continue
		}
		path, err := exec.LookPath(tool)
		if err != nil {
			// Absent entirely: the shell reports that itself, with its own message.
			continue
		}
		if isSystem32Binary(path) {
			misrouted = append(misrouted, tool+" -> "+path)
		}
	}
	if len(misrouted) > 0 {
		return fmt.Errorf("cmd: discovery would run Windows programs that are not the POSIX ones: %s. "+
			"Put Git's usr\\bin ahead of %%SystemRoot%%\\System32 on PATH, or point discover.from at a file "+
			"instead of a command", strings.Join(misrouted, ", "))
	}
	return nil
}

// isSystem32Binary reports whether path resolves inside %SystemRoot%\System32,
// which is where the conflicting Windows tools live.
func isSystem32Binary(path string) bool {
	root := os.Getenv("SystemRoot")
	if strings.TrimSpace(root) == "" {
		root = `C:\Windows`
	}
	system32 := filepath.Join(root, "System32")
	abs, err := filepath.Abs(path)
	if err != nil {
		return false
	}
	rel, err := filepath.Rel(filepath.Clean(system32), filepath.Clean(abs))
	if err != nil {
		return false
	}
	return rel != "." && rel != ".." && !strings.HasPrefix(rel, ".."+string(filepath.Separator))
}

// mentionsTool reports whether the script names tool as a whole word, so
// "findings" does not count as "find". A false positive would only make the
// preflight stricter than necessary.
func mentionsTool(script, tool string) bool {
	fields := strings.FieldsFunc(script, func(r rune) bool {
		switch {
		case r >= 'a' && r <= 'z', r >= 'A' && r <= 'Z', r >= '0' && r <= '9':
			return false
		case r == '-' || r == '_' || r == '.' || r == '/':
			return false
		}
		return true
	})
	for _, f := range fields {
		if strings.EqualFold(f, tool) {
			return true
		}
	}
	return false
}
