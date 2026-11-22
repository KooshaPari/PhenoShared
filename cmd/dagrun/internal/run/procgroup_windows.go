//go:build windows

package run

import (
	"os/exec"
	"strconv"
	"time"
)

// setProcessGroup makes a cancelled harness actually stop on Windows.
//
// Two separate gaps, both observed rather than assumed:
//
//   - killing the shell leaves its children running, so a harness that spawned a
//     grandchild kept working after the deadline;
//   - the grandchild also holds the output pipe open, and Wait blocks on that pipe,
//     so even a successful kill did not return. WaitDelay bounds it.
//
// taskkill /T is the process-tree kill Windows provides; the job-object route would
// avoid the extra process, but this needs no handle juggling and is available
// everywhere.
func setProcessGroup(cmd *exec.Cmd) {
	cmd.WaitDelay = 10 * time.Second
	cmd.Cancel = func() error {
		if cmd.Process == nil {
			return nil
		}
		pid := strconv.Itoa(cmd.Process.Pid)
		_ = exec.Command("taskkill", "/T", "/F", "/PID", pid).Run()
		// Kill returns an error once the process is already gone, and taskkill has
		// handled it by then, so a failure here is not worth propagating.
		_ = cmd.Process.Kill()
		return nil
	}
}
