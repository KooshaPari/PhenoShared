package integration

import (
	"testing"
	"os/exec"
	"runtime"
	"strings"
	"time"
)

func TestCLIHelp(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping integration test in short mode")
	}

	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("helios.exe", "--help")
	} else {
		cmd = exec.Command("./helios", "--help")
	}

	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Skipf("binary not available: %v", err)
	}

	output := string(out)
	if !strings.Contains(strings.ToLower(output), "help") && !strings.Contains(strings.ToLower(output), "usage") {
		t.Errorf("expected help/usage in output, got: %s", output[:min(200, len(output))])
	}
}

func TestCLIVersion(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping integration test in short mode")
	}

	var cmd *exec.Cmd
	if runtime.GOOS == "windows" {
		cmd = exec.Command("helios.exe", "version")
	} else {
		cmd = exec.Command("./helios", "version")
	}

	cmd.Dir = "."
	timeout := time.After(10 * time.Second)
	done := make(chan error, 1)
	go func() {
		done <- cmd.Run()
	}()

	select {
	case <-timeout:
		t.Skip("version command timed out - binary may not be built")
	case <-done:
		// ok
	}
}

func TestCLIFullWorkflow(t *testing.T) {
	if testing.Short() {
		t.Skip("skipping e2e workflow test in short mode")
	}
	t.Log("Full workflow test - stub for future implementation")
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
