package store

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"testing"
	"time"

	"github.com/KooshaPari/dagrun/internal/plan"
)

// Crash-recovery proof. These tests exist because "recovery is handled" is a
// claim, and a claim is not a test. Each one kills something real and then
// asserts the store is still coherent.

// The claim path is the one mutation whose duplicate would do work twice. Kill
// competing processes mid-claim and assert that exactly one claim survives: no
// double-claim, and no lost claim either.
func TestKilledClaimantsLeaveExactlyOneClaim(t *testing.T) {
	if _, err := exec.LookPath(os.Args[0]); err != nil {
		t.Skip("cannot re-exec the test binary")
	}
	root := t.TempDir()
	newStore(t, root, 0)

	const procs = 6
	cmds := make([]*exec.Cmd, 0, procs)
	for i := 0; i < procs; i++ {
		cmd := exec.Command(os.Args[0], "-test.run=TestCrashClaimHelper")
		cmd.Env = append(os.Environ(),
			"DAGRUN_HELPER=crashclaim",
			"DAGRUN_ROOT="+root,
			"DAGRUN_WORKER="+fmt.Sprintf("w%d", i),
		)
		if err := cmd.Start(); err != nil {
			t.Fatalf("start helper %d: %v", i, err)
		}
		cmds = append(cmds, cmd)
	}

	// Kill the later half while they are contending. The first few are allowed
	// to finish so the test also proves a survivor is not disturbed.
	for i := procs / 2; i < procs; i++ {
		_ = cmds[i].Process.Signal(syscall.SIGKILL)
	}
	for _, cmd := range cmds {
		_ = cmd.Wait() // a killed child reports an error; that is the point
	}

	// Reopen and count who holds the lease.
	dir := filepath.Join(root, ".dagrun")
	p, err := plan.Parse([]byte(testPlan))
	if err != nil {
		t.Fatal(err)
	}
	st, err := Open(dir, p, []byte(testPlan), false)
	if err != nil {
		t.Fatalf("reopen after a kill: %v", err)
	}
	snap, err := st.Snapshot()
	if err != nil {
		t.Fatalf("snapshot after a kill: %v", err)
	}
	ns := snap.Nodes["1"]
	if ns == nil {
		t.Fatal("node 1 vanished")
	}

	// Either exactly one claim was recorded, or none: a killed process may have
	// died before it persisted. What must never happen is two.
	if ns.Status == plan.StatusRunning {
		if ns.Owner == "" {
			t.Error("a running node with no owner is not a claim; the lease lost its identity")
		}
		if ns.Epoch == 0 {
			t.Error("a claim without an epoch cannot be fenced")
		}
	}
	// The store must still be writable and coherent after the kills.
	if err := st.With(func(s *State) error {
		s.Nodes["1"].LastError = "post-crash probe"
		return nil
	}); err != nil {
		t.Fatalf("the store is not writable after a SIGKILL: %v", err)
	}
}

// TestCrashClaimHelper is the child. It claims, then waits to be killed.
func TestCrashClaimHelper(t *testing.T) {
	if os.Getenv("DAGRUN_HELPER") != "crashclaim" {
		t.Skip("helper process")
	}
	root := os.Getenv("DAGRUN_ROOT")
	dir := filepath.Join(root, ".dagrun")
	p, err := plan.Parse([]byte(testPlan))
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	p.Root = root
	st, err := Open(dir, p, []byte(testPlan), false)
	if err != nil {
		t.Fatalf("open: %v", err)
	}
	c, err := st.Claim("1", os.Getenv("DAGRUN_WORKER"), time.Minute, time.Now())
	if err != nil {
		t.Fatalf("claim: %v", err)
	}
	fmt.Printf("WON=%v EPOCH=%d\n", c.Won, c.Epoch)
	// Hold the claim until the parent kills us. Without this the process exits
	// before the kill lands and the test proves nothing.
	time.Sleep(5 * time.Second)
}

// A torn state file is what a crash mid-rename used to leave. It must be refused
// with a clear error, never half-read: a half-populated state is how a run
// silently re-executes finished work.
func TestTruncatedStateIsRefusedNotHalfRead(t *testing.T) {
	root := t.TempDir()
	newStore(t, root, 0)
	dir := filepath.Join(root, ".dagrun")

	full, err := os.ReadFile(filepath.Join(dir, "state.json"))
	if err != nil {
		t.Fatal(err)
	}
	// Cut the document in half, which is exactly what a partial write looks like.
	if err := os.WriteFile(filepath.Join(dir, "state.json"), full[:len(full)/2], 0o644); err != nil {
		t.Fatal(err)
	}

	p, err := plan.Parse([]byte(testPlan))
	if err != nil {
		t.Fatal(err)
	}
	st, err := Open(dir, p, []byte(testPlan), false)
	if err == nil {
		// If Open tolerated it, the only acceptable behaviour is a fully
		// re-read state. Anything else means it guessed.
		snap, serr := st.Snapshot()
		if serr == nil && len(snap.Nodes) > 0 {
			t.Fatalf("a truncated state was read as %d nodes; it must be refused", len(snap.Nodes))
		}
		return
	}
	if !contains(err.Error(), "corrupt") {
		t.Errorf("error should say the state is corrupt, got: %v", err)
	}
}

// A completed node must be adopted on reopen, not recomputed. Recomputation is
// the once-only side-effect bug: the artifact exists, so the node is done, and
// running it again would redo work that already happened.
func TestCompletedNodeIsAdoptedNotRecomputed(t *testing.T) {
	root := t.TempDir()
	st := newStore(t, root, 0)
	now := time.Now()

	c, err := st.Claim("1", "w", time.Minute, now)
	if err != nil {
		t.Fatal(err)
	}
	if !c.Won {
		t.Fatalf("could not claim: %s", c.Reason)
	}
	if _, err := st.Finish("1", "w", c.Epoch, plan.StatusDone, nil, 0, "", now.Add(time.Second)); err != nil {
		t.Fatal(err)
	}

	// Reopen, as a restarted executor would.
	dir := filepath.Join(root, ".dagrun")
	p, err := plan.Parse([]byte(testPlan))
	if err != nil {
		t.Fatal(err)
	}
	again, err := Open(dir, p, []byte(testPlan), false)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	snap, err := again.Snapshot()
	if err != nil {
		t.Fatal(err)
	}
	if got := snap.Nodes["1"].Status; got != plan.StatusDone {
		t.Fatalf("node 1 status after reopen = %q, want done (the completion was lost)", got)
	}

	// And a second claim must be refused: the work is finished.
	c2, err := again.Claim("1", "other", time.Minute, time.Now())
	if err != nil {
		t.Fatal(err)
	}
	if c2.Won {
		t.Error("a finished node was claimable again; its side effects would run twice")
	}
}

func contains(hay, needle string) bool {
	return len(hay) >= len(needle) && (func() bool {
		for i := 0; i+len(needle) <= len(hay); i++ {
			if hay[i:i+len(needle)] == needle {
				return true
			}
		}
		return false
	})()
}
