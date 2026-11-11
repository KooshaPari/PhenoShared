//go:build windows

package hook

import "os/exec"

// setProcessGroup is a no-op on Windows: there are no process groups to
// isolate. The runner still bounds how long it waits for the hook.
func setProcessGroup(cmd *exec.Cmd) {
	cmd.WaitDelay = waitDelay
}
