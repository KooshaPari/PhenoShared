//go:build windows

package applet

import "os"

// ProcessAlive reports whether pid names a live process.
//
// On Windows there is no signal 0, so this asks the process table for the handle
// instead: FindProcess fails when the pid is unused. A successful open is closed
// immediately. The same caveat as the Unix version applies and is why callers
// also fetch the advertisement's own manifest before deleting it: a handle that
// opens proves a pid is in use, not that the server behind it is still the same
// one.
func ProcessAlive(pid int) bool {
	if pid <= 0 {
		return false
	}
	p, err := os.FindProcess(pid)
	if err != nil {
		return false
	}
	_ = p.Release()
	return true
}
