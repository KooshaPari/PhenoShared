//go:build windows

package mcp

import (
	"os/exec"
	"testing"
	"time"
)

// stopAndExpectCleanExit stops the server the only way a test can on Windows.
//
// There is no SIGTERM: Process.Signal rejects it with "signal: not supported by
// windows", and a real Ctrl+C is delivered by the console rather than by a
// signal call, so a spawned test process cannot receive one. Killing the
// process keeps the serve-and-handshake half of the test (the part that proves
// the HTTP transport works) while dropping the clean-exit claim, which unix
// covers. A graceful Windows shutdown needs a console control event and is not
// asserted here.
func stopAndExpectCleanExit(t *testing.T, cmd *exec.Cmd, stderr string) {
	t.Helper()
	if err := cmd.Process.Kill(); err != nil {
		t.Fatalf("kill: %v", err)
	}
	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()
	select {
	case <-done:
	case <-time.After(15 * time.Second):
		t.Fatalf("the server did not exit after Kill\nstderr: %s", stderr)
	}
	t.Log("clean shutdown on SIGTERM is unix-only; Windows has no SIGTERM to send")
}
