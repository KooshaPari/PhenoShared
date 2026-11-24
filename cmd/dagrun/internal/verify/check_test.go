package verify

import (
	"context"
	"strings"
	"testing"
	"time"
)

// TestRunCheckEchoesOutput proves a check command actually runs through the
// platform shell selected by shellCommand, on unix and on Windows alike.
func TestRunCheckEchoesOutput(t *testing.T) {
	dir := t.TempDir()
	rep := runCheck(context.Background(), dir, "echo dagrun-check-ok", 30*time.Second)
	if !rep.OK {
		t.Fatalf("check failed: exit=%d output=%q", rep.ExitCode, rep.Output)
	}
	if !strings.Contains(rep.Output, "dagrun-check-ok") {
		t.Fatalf("output %q does not contain the echoed token", rep.Output)
	}
}

// TestRunCheckReportsNonZeroExit keeps the failure path honest: a check that
// exits non-zero must not be recorded as OK.
func TestRunCheckReportsNonZeroExit(t *testing.T) {
	dir := t.TempDir()
	rep := runCheck(context.Background(), dir, "exit 3", 30*time.Second)
	if rep.OK {
		t.Fatalf("check %q reported OK, want failure", "exit 3")
	}
	if rep.ExitCode != 3 {
		t.Fatalf("exit code = %d, want 3", rep.ExitCode)
	}
}
