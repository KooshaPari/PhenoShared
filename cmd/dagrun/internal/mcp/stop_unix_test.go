//go:build !windows

package mcp

import (
	"os/exec"
	"syscall"
	"testing"
	"time"
)

// stopAndExpectCleanExit asks the server to stop the way a supervisor would on
// unix and requires exit 0: a stop is not a failure.
func stopAndExpectCleanExit(t *testing.T, cmd *exec.Cmd, stderr string) {
	t.Helper()
	if err := cmd.Process.Signal(syscall.SIGTERM); err != nil {
		t.Fatalf("signal: %v", err)
	}
	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("the server exited with %v on SIGTERM; a stop must exit 0\nstderr: %s", err, stderr)
		}
	case <-time.After(15 * time.Second):
		t.Fatal("the server did not stop on SIGTERM")
	}
}
