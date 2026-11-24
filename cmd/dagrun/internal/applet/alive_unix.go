//go:build !windows

package applet

import (
	"errors"
	"syscall"
)

// ProcessLiveness reports what a pid probe could establish.
//
// Signal 0 performs the existence and permission checks without delivering
// anything, which is the only portable-on-Unix way to ask about a pid without
// touching the process. The three outcomes are kept apart on purpose:
//
//	nil   - a process holds this pid (LivenessAlive)
//	EPERM - a process holds this pid and belongs to someone else
//	        (LivenessUnknown, NOT dead)
//	ESRCH - no process holds this pid (LivenessDead)
//
// Collapsing EPERM into "dead" deletes another user's advertisement. Collapsing
// it into "alive" leaves a recycled pid holding a record forever, which is why
// callers also probe the record's own manifest before deleting anything and why
// "alive" never authorises deletion by itself.
//
// A wrong pid is possible and is never the deciding evidence on its own.
func ProcessLiveness(pid int) Liveness {
	if pid <= 0 {
		// No process can hold a non-positive pid, so nothing is being guessed.
		return LivenessDead
	}
	err := syscall.Kill(pid, 0)
	switch {
	case err == nil:
		return LivenessAlive
	case errors.Is(err, syscall.EPERM):
		// Askable refuses, so the pid is in use by somebody. That is closer to
		// alive than to dead, and it is certainly not proof of absence.
		return LivenessUnknown
	case errors.Is(err, syscall.ESRCH):
		return LivenessDead
	default:
		// Any other failure is unreadable, not evidence of death. Keeping a
		// stale record is recoverable; deleting a live one is not.
		return LivenessUnknown
	}
}
