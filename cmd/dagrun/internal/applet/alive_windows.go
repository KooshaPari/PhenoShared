//go:build windows

package applet

import (
	"errors"
	"syscall"
)

// Windows has no signal 0, so liveness is asked of the process table: open the
// process and read its exit code. The two error branches are the whole point of
// this file, because Windows reports "you may not ask" and "nothing is there"
// with different codes and only one of them means the pid is free.
//
//	ERROR_INVALID_PARAMETER - no process with that pid. The one true "dead".
//	ERROR_ACCESS_DENIED     - a process with that pid exists and refuses the
//	                          query. System, services, other users' processes.
//
// Collapsing the second into false is not a conservative default here: it made
// `dagrun instances --prune` delete the advertisement of a live pid, measured
// against pid 4 on the desk. A pid you cannot open is not a pid that is gone.
const (
	// processQueryLimitedInformation asks for enough to read the exit code
	// without requesting the rights that make protected processes refuse.
	// It needs no elevation.
	processQueryLimitedInformation = 0x1000

	// stillActive is the exit code a process that has not exited reports.
	stillActive = 259

	// errInvalidParameter is ERROR_INVALID_PARAMETER (87). The syscall package
	// names ERROR_ACCESS_DENIED but not this one, and a bare number at the call
	// site would read as a magic constant.
	errInvalidParameter = syscall.Errno(87)
)

// ProcessAlive reports whether pid names a live process.
//
// A pid being in use does not prove the server that advertised it is still the
// same process: pids are recycled, and this is why callers also probe the
// advertisement's own manifest before deleting it. It does prove that deleting
// the record would be a guess.
func ProcessAlive(pid int) bool {
	if pid <= 0 {
		return false
	}
	h, err := syscall.OpenProcess(processQueryLimitedInformation, false, uint32(pid))
	if err != nil {
		switch {
		case errors.Is(err, errInvalidParameter):
			return false
		case errors.Is(err, syscall.ERROR_ACCESS_DENIED):
			return true
		default:
			// Any other failure is unreadable, not evidence of death. Keeping
			// a stale record is recoverable; deleting a live one is not.
			return true
		}
	}
	defer syscall.CloseHandle(h)
	var code uint32
	if err := syscall.GetExitCodeProcess(h, &code); err != nil {
		return true
	}
	return code == stillActive
}
