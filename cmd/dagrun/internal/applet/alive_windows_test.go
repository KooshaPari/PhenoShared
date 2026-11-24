//go:build windows

package applet

import (
	"os"
	"os/exec"
	"syscall"
	"testing"
)

// The bug these tests pin: FindProcess failing was read as "dead", so a
// protected process looked free and its advertisement was pruned while it was
// still serving. pid 4 is the clearest case -- it always exists on Windows and
// is usually unopenable without elevation.
func TestProcessAliveCannotBeConfusedWithPermission(t *testing.T) {
	if !ProcessAlive(4) {
		t.Fatalf("pid 4 (System) reported dead; an unopenable pid is not a free pid")
	}
}

func TestProcessAliveCurrentProcess(t *testing.T) {
	if !ProcessAlive(os.Getpid()) {
		t.Fatalf("the running process reported itself dead")
	}
}

func TestProcessAliveRejectsNonPositive(t *testing.T) {
	for _, pid := range []int{0, -1} {
		if ProcessAlive(pid) {
			t.Fatalf("ProcessAlive(%d) = true, want false", pid)
		}
	}
}

func TestProcessAliveExitedProcess(t *testing.T) {
	cmd := exec.Command("cmd", "/c", "exit", "0")
	if err := cmd.Start(); err != nil {
		t.Fatalf("start: %v", err)
	}
	pid := cmd.Process.Pid
	if err := cmd.Wait(); err != nil {
		t.Fatalf("wait: %v", err)
	}
	if ProcessAlive(pid) {
		t.Fatalf("an exited process (pid %d) reported alive", pid)
	}
}

func TestProcessAliveUnusedPID(t *testing.T) {
	// Find a pid the kernel itself reports as absent, so the assertion is about
	// ERROR_INVALID_PARAMETER rather than about a pid we merely hope is unused.
	pid := 0
	for candidate := 60000; candidate < 65000; candidate++ {
		h, err := syscall.OpenProcess(processQueryLimitedInformation, false, uint32(candidate))
		if err == nil {
			syscall.CloseHandle(h)
			continue
		}
		if errorsIsInvalidParameter(err) {
			pid = candidate
			break
		}
	}
	if pid == 0 {
		t.Skip("no unused pid in the scanned range")
	}
	if ProcessAlive(pid) {
		t.Fatalf("unused pid %d reported alive", pid)
	}
}

func errorsIsInvalidParameter(err error) bool {
	return err != nil && err == errInvalidParameter
}
