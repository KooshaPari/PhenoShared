//go:build windows

package hook

import "os/exec"

// setProcessGroup leaves the command untouched on Windows: process groups are
// a POSIX concept and do not exist there. The runner still bounds how long it
// waits for the hook.
func setProcessGroup(cmd *exec.Cmd) {
	cmd.WaitDelay = waitDelay
}
