//go:build !windows

package applet

import (
	"os"
	"os/exec"
	"testing"
)

// undeadPID is a pid no process can hold on any target we build for: macOS caps
// pids at kern.maxproc (99999), Linux defaults to 4194304, and Windows
// allocation never reaches it.
const undeadPID = 4194305

func TestProcessLivenessCurrentProcess(t *testing.T) {
	if got := ProcessLiveness(os.Getpid()); got != LivenessAlive {
		t.Fatalf("the running process reported %s, want alive", got)
	}
}

// A non-positive pid cannot be held by anything, so "dead" here is a fact
// rather than a probe result. It must never be reported as unknown, or every
// record with an unset pid would be immortal.
func TestProcessLivenessRejectsNonPositive(t *testing.T) {
	for _, pid := range []int{0, -1} {
		if got := ProcessLiveness(pid); got != LivenessDead {
			t.Fatalf("ProcessLiveness(%d) = %s, want dead", pid, got)
		}
	}
}

func TestProcessLivenessUnusedPID(t *testing.T) {
	if got := ProcessLiveness(undeadPID); got != LivenessDead {
		t.Fatalf("unused pid %d reported %s, want dead", undeadPID, got)
	}
}

func TestProcessLivenessExitedProcess(t *testing.T) {
	cmd := exec.Command("true")
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

// The regression. EPERM means a process holds the pid and refuses to be
// signalled, which is the opposite of a free pid. Reading it as dead is what
// deleted another user's advertisement; the tri-state reports unknown so no
// caller can act on it as absence.
//
// pid 1 is the portable non-root case: as an unprivileged user, signal 0 against
// init returns EPERM on Linux and macOS alike. Running as root, pid 1 answers
// and this fixture says nothing about the denied branch, so it skips and states
// why rather than passing for the wrong reason.
func TestProcessLivenessUnaskablePIDIsUnknown(t *testing.T) {
	if os.Geteuid() == 0 {
		t.Skip("running as root: signal 0 against pid 1 succeeds, so the EPERM branch cannot be exercised")
	}
	if got := ProcessLiveness(1); got != LivenessUnknown {
		t.Fatalf("pid 1 reported %s, want unknown (EPERM is not absence)", got)
	}
}
