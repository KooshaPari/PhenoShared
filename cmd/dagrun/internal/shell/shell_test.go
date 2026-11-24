package shell

import (
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// TestCommandRunsOnThisPlatform proves Command returns something that actually
// executes, on unix and on Windows alike, rather than only the right shape.
func TestCommandRunsOnThisPlatform(t *testing.T) {
	name, args := Command("echo dagrun-shell-ok")
	out, err := exec.Command(name, args...).CombinedOutput()
	if err != nil {
		t.Fatalf("%s %v: %v\n%s", name, args, err, out)
	}
	if !strings.Contains(string(out), "dagrun-shell-ok") {
		t.Fatalf("output %q does not contain the echoed token", out)
	}
}

// resolvedShellName is the interpreter Command picks for this platform.
func resolvedShellName() string {
	name, _ := Command("")
	return name
}

// exitThreeCommandFor returns a command string that exits with status 3 under
// the interpreter named by Command. cmd needs `exit /b`; sh needs `exit`.
func exitThreeCommandFor(name string) string {
	if base := filepath.Base(name); base == "cmd" || base == "cmd.exe" {
		return "exit /b 3"
	}
	return "exit 3"
}

// TestCommandReportsNonZeroExit keeps the failure path honest: a non-zero exit
// must survive the interpreter, or every check would look successful.
func TestCommandReportsNonZeroExit(t *testing.T) {
	// The command text depends on which interpreter Command picked, not on the
	// build: a Windows box with Git for Windows has sh, and `exit /b 3` under sh
	// exits 2 ("exit: Illegal number: /b").
	exitText := exitThreeCommandFor(resolvedShellName())
	name, args := Command(exitText)
	err := exec.Command(name, args...).Run()
	exitErr, ok := err.(*exec.ExitError)
	if !ok {
		t.Fatalf("err = %v, want an ExitError carrying exit code 3", err)
	}
	if code := exitErr.ExitCode(); code != 3 {
		t.Fatalf("exit code = %d, want 3", code)
	}
}
