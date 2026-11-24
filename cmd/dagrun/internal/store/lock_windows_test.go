//go:build windows

package store

import (
	"os"
	"os/exec"
	"path/filepath"
	"testing"
	"time"
)

// Lock-level proof for the Windows path. store.go depends on exactly two
// properties from the lock: a second writer blocks instead of interleaving,
// and the OS drops the lock when its holder goes away (which is why there is
// no stale-lock cleanup path anywhere in this codebase). Both are asserted
// against a real child process, because "cross-process" is the property that
// matters -- a second goroutine would prove nothing about LockFileEx.
//
// These tests only exist on Windows: on Unix the equivalent behaviour is
// flock(2), which the platform already provides.

const (
	lockHelperMode   = "DAGRUN_LOCK_HELPER"
	lockHelperPath   = "DAGRUN_LOCK_PATH"
	lockHelperResult = "DAGRUN_LOCK_RESULT"
	// How long "the other side did not get in" is observed before the lock is
	// treated as live. Long enough to cover process start, short enough that
	// the suite stays fast.
	lockContentionWindow = 700 * time.Millisecond
	lockAcquireDeadline  = 15 * time.Second
)

// TestWindowsLockHelper is the child half of the tests below. It is skipped in
// every ordinary run and only does work when the parent sets the mode.
func TestWindowsLockHelper(t *testing.T) {
	mode := os.Getenv(lockHelperMode)
	if mode == "" {
		t.Skip("helper process")
	}
	path := os.Getenv(lockHelperPath)
	result := os.Getenv(lockHelperResult)
	if path == "" || result == "" {
		t.Fatal("helper needs a lock path and a result path")
	}

	f, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0o644)
	if err != nil {
		t.Fatalf("open lock: %v", err)
	}
	defer f.Close()

	if err := lockExclusive(f); err != nil {
		t.Fatalf("lockExclusive: %v", err)
	}
	// The file appearing is the evidence that this process holds the lock.
	if err := os.WriteFile(result, []byte("acquired"), 0o644); err != nil {
		t.Fatalf("announce: %v", err)
	}

	if mode == "hold" {
		// Hold until the parent kills us. That kill is the test in
		// TestKilledHolderReleasesLock, so this has to outlive it.
		time.Sleep(60 * time.Second)
	}

	if err := unlock(f); err != nil {
		t.Fatalf("unlock: %v", err)
	}
}

// TestLockBlocksSecondHolderAndReleases proves contention, then release: the
// child cannot take the lock while the parent holds it, takes it once the
// parent unlocks, and the parent can take it again afterwards (so unlock is a
// real release and not just a closed handle).
func TestLockBlocksSecondHolderAndReleases(t *testing.T) {
	dir := t.TempDir()
	lockPath := filepath.Join(dir, "lock")
	resultPath := filepath.Join(dir, "child-result")

	held, err := os.OpenFile(lockPath, os.O_CREATE|os.O_RDWR, 0o644)
	if err != nil {
		t.Fatalf("open lock: %v", err)
	}
	defer held.Close()
	if err := lockExclusive(held); err != nil {
		t.Fatalf("parent lockExclusive: %v", err)
	}

	child := startLockHelper(t, "wait", lockPath, resultPath)
	defer stopLockHelper(child)

	if waitForFile(resultPath, lockContentionWindow) {
		t.Fatal("child acquired the lock while the parent still held it")
	}

	if err := unlock(held); err != nil {
		t.Fatalf("parent unlock: %v", err)
	}
	if !waitForFile(resultPath, lockAcquireDeadline) {
		t.Fatal("child never acquired the lock after the parent released it")
	}
	if err := child.Wait(); err != nil {
		t.Fatalf("child exit: %v", err)
	}

	if err := lockExclusive(held); err != nil {
		t.Fatalf("parent re-acquire after release: %v", err)
	}
	if err := unlock(held); err != nil {
		t.Fatalf("parent final unlock: %v", err)
	}
}

// TestKilledHolderReleasesLock proves the property that lets store.go carry no
// stale-lock cleanup: kill the holder while it owns the lock, and a process
// already waiting on it must proceed.
func TestKilledHolderReleasesLock(t *testing.T) {
	dir := t.TempDir()
	lockPath := filepath.Join(dir, "lock")
	holderResult := filepath.Join(dir, "holder-result")
	waiterResult := filepath.Join(dir, "waiter-result")

	holder := startLockHelper(t, "hold", lockPath, holderResult)
	if !waitForFile(holderResult, lockAcquireDeadline) {
		stopLockHelper(holder)
		t.Fatal("holder never acquired the lock")
	}

	waiter := startLockHelper(t, "wait", lockPath, waiterResult)
	defer stopLockHelper(waiter)

	if waitForFile(waiterResult, lockContentionWindow) {
		t.Fatal("waiter acquired the lock while the holder was alive and holding it")
	}

	if err := holder.Process.Kill(); err != nil {
		t.Fatalf("kill holder: %v", err)
	}
	_ = holder.Wait() // a killed child reports an error; that is the point

	if !waitForFile(waiterResult, lockAcquireDeadline) {
		t.Fatal("waiter never acquired the lock after the holder was killed: the lock outlived its owner")
	}
	if err := waiter.Wait(); err != nil {
		t.Fatalf("waiter exit: %v", err)
	}
}

func startLockHelper(t *testing.T, mode, lockPath, resultPath string) *exec.Cmd {
	t.Helper()
	cmd := exec.Command(os.Args[0], "-test.run=TestWindowsLockHelper")
	cmd.Env = append(os.Environ(),
		lockHelperMode+"="+mode,
		lockHelperPath+"="+lockPath,
		lockHelperResult+"="+resultPath,
	)
	if err := cmd.Start(); err != nil {
		t.Fatalf("start %s helper: %v", mode, err)
	}
	return cmd
}

func stopLockHelper(cmd *exec.Cmd) {
	if cmd == nil || cmd.Process == nil {
		return
	}
	_ = cmd.Process.Kill()
	_ = cmd.Wait()
}

// waitForFile reports whether path appeared within d.
func waitForFile(path string, d time.Duration) bool {
	deadline := time.Now().Add(d)
	for {
		if _, err := os.Stat(path); err == nil {
			return true
		}
		if time.Now().After(deadline) {
			return false
		}
		time.Sleep(20 * time.Millisecond)
	}
}
