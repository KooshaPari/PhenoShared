//go:build windows

package verify

import (
	"os/exec"
	"strconv"
	"time"
)

// setProcessGroup makes a cancelled verify command actually stop on Windows.
//
// Killing the shell is not enough: a check that spawns children leaves them running,
// and they keep the output pipe open so Wait blocks well past the deadline. taskkill
// /T removes the subtree and WaitDelay bounds the pipe wait.
func setProcessGroup(cmd *exec.Cmd) {
	cmd.WaitDelay = 10 * time.Second
	cmd.Cancel = func() error {
		if cmd.Process == nil {
			return nil
		}
		pid := strconv.Itoa(cmd.Process.Pid)
		_ = exec.Command("taskkill", "/T", "/F", "/PID", pid).Run()
		_ = cmd.Process.Kill()
		return nil
	}
}
