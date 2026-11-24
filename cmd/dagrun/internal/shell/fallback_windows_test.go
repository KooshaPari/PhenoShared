//go:build windows

package shell

import (
	"os"
	"os/exec"
	"testing"
)

// TestCommandFallsBackToCmdWhenNoShOnPath covers the Windows box that has no
// POSIX shell at all: before the fallback existed every check and every hook
// failed with "executable file not found" instead of running the command.
func TestCommandFallsBackToCmdWhenNoShOnPath(t *testing.T) {
	restrictPathToSystem32(t)

	name, args := Command("dir /b")
	if name != "cmd" {
		t.Fatalf("shell = %q, want cmd when no sh is on PATH", name)
	}
	if len(args) != 2 || args[0] != "/c" {
		t.Fatalf("args = %v, want [/c <command>]", args)
	}
	// The fallback has to actually run the command, not merely be named cmd.
	out, err := exec.Command(name, args...).CombinedOutput()
	if err != nil {
		t.Fatalf("%s %v: %v\n%s", name, args, err, out)
	}
}

// restrictPathToSystem32 hides every non-system directory from PATH so the
// lookup above cannot find a Git-for-Windows sh.
func restrictPathToSystem32(t *testing.T) {
	t.Helper()
	old, had := os.LookupEnv("PATH")
	t.Cleanup(func() {
		if had {
			_ = os.Setenv("PATH", old)
			return
		}
		_ = os.Unsetenv("PATH")
	})
	if err := os.Setenv("PATH", `C:\Windows\System32`); err != nil {
		t.Fatalf("set PATH: %v", err)
	}
}
