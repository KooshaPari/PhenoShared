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
//
// The tri-state makes the distinction explicit rather than implicit: the probe
// reports "unknown", which no caller may read as permission to delete.
func TestProcessLivenessCannotBeConfusedWithPermission(t *testing.T) {
	switch got := ProcessLiveness(4); got {
	case LivenessUnknown, LivenessAlive:
		// Both retain the record. Which one appears depends on whether this run
		// can open the System process at all, and that is not the assertion.
	default:
		t.Fatalf("pid 4 (System) reported %s; an unopenable pid is not a free pid", got)
	}
}

func TestProcessLivenessCurrentProcess(t *testing.T) {
	if got := ProcessLiveness(os.Getpid()); got != LivenessAlive {
		t.Fatalf("the running process reported %s, want alive", got)
	}
}

func TestProcessLivenessRejectsNonPositive(t *testing.T) {
	for _, pid := range []int{0, -1} {
		if got := ProcessLiveness(pid); got != LivenessDead {
			t.Fatalf("ProcessLiveness(%d) = %s, want dead", pid, got)
		}
	}
}

// Wait reaps the process, so the pid is released and the probe should find it
// free. A pid recycled into an unrelated live process between Wait and the
// probe would fail this test; that is a real possibility on a busy host rather
// than a defect, and it fails loudly instead of hiding.
func TestProcessLivenessExitedProcess(t *testing.T) {
	cmd := exec.Command("cmd", "/c", "exit", "0")
	if err := cmd.Start(); err != nil {
		t.Fatalf("start: %v", err)
	}
	pid := cmd.Process.Pid
	if err := cmd.Wait(); err != nil {
		t.Fatalf("wait: %v", err)
	}
	if got := ProcessLiveness(pid); got != LivenessDead {
		t.Fatalf("an exited process (pid %d) reported %s, want dead", pid, got)
	}
}

func TestProcessLivenessUnusedPID(t *testing.T) {
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
	if got := ProcessLiveness(pid); got != LivenessDead {
		t.Fatalf("unused pid %d reported %s, want dead", pid, got)
	}
}

func errorsIsInvalidParameter(err error) bool {
	return err != nil && err == errInvalidParameter
}
