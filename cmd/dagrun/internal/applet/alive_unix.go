//go:build !windows

package applet

import (
	"errors"
	"syscall"
)

// ProcessAlive reports whether pid names a live process.
//
// Signal 0 performs the existence and permission checks without delivering
// anything, which is the only portable-on-Unix way to ask "is this pid in use"
// without touching the process. EPERM means the process exists but belongs to
// someone else, so it counts as alive: treating it as dead would delete another
// user's advertisement.
//
// A wrong pid is possible and is never the deciding evidence on its own. Callers
// pair this with a fetch of the advertisement's own manifest, so a recycled pid
// cannot keep a dead server's file forever.
func ProcessAlive(pid int) bool {
	if pid <= 0 {
		return false
	}
	err := syscall.Kill(pid, 0)
	if err == nil {
		return true
	}
	return errors.Is(err, syscall.EPERM)
}
