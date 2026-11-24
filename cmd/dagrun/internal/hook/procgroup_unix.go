//go:build !windows

package hook

import (
	"os/exec"
	"syscall"
)

// setProcessGroup isolates the hook so that a deadline kills the whole subtree,
// not just the shell.
//
// Without this, `sh -c "sleep 30"` leaves the sleep running when the shell is
// killed: the child keeps the output pipe open, so the runner waits for the
// sleep to finish and the deadline is not enforced. Some shells exec the
// command and some fork it, so the behaviour differed by host.
func setProcessGroup(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	cmd.Cancel = func() error {
		if cmd.Process == nil {
			return nil
		}
		// A negative pid signals the whole group, so a forked child dies too.
		return syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
	}
	// Bound the wait: if something escaped the group and still holds the pipe,
	// stop waiting for it instead of running to the hook's full duration.
	cmd.WaitDelay = waitDelay
}
