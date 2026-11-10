package recover

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// The plan fixture mirrors the shape internal/store's tests use: a run.yaml
// that plan.Parse accepts and that names every node the state talks about.
const testPlan = `
version: 1
run: recovertest
nodes:
  - id: "1"
    kind: IMPL
    role: impl
    artifacts: [{path: a}]
  - id: "2"
    kind: IMPL
    role: impl
    artifacts: [{path: b}]
  - id: "3"
    kind: IMPL
    role: docs
    artifacts: [{path: c}]
  - id: "4"
    kind: IMPL
    role: docs
    artifacts: [{path: d}]
`

// runFixture is a run directory with a plan installed and no state written yet.
type runFixture struct {
	dir string
}

func newRun(t *testing.T) runFixture {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), []byte(testPlan), 0o644); err != nil {
		t.Fatalf("write run.yaml: %v", err)
	}
	return runFixture{dir: dir}
}

// withState writes a state document. It marshals the real store.State type
// rather than a hand-written JSON blob, so the fixture cannot drift from the
// schema the package actually reads.
func (f runFixture) withState(t *testing.T, nodes map[string]*store.NodeState) {
	t.Helper()
	st := &store.State{
		Version:   store.StateVersion,
		Run:       "recovertest",
		CreatedAt: time.Now().UTC(),
		UpdatedAt: time.Now().UTC(),
		Nodes:     nodes,
	}
	raw, err := json.Marshal(st)
	if err != nil {
		t.Fatalf("marshal state: %v", err)
	}
	if err := os.WriteFile(filepath.Join(f.dir, "state.json"), append(raw, '\n'), 0o644); err != nil {
		t.Fatalf("write state.json: %v", err)
	}
}

// readState reads the on-disk state back, so a mutation is asserted against the
// bytes that were persisted rather than against the callback's input.
func (f runFixture) readState(t *testing.T) *store.State {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join(f.dir, "state.json"))
	if err != nil {
		t.Fatalf("read state.json: %v", err)
	}
	var st store.State
	if err := json.Unmarshal(raw, &st); err != nil {
		t.Fatalf("unmarshal state.json: %v", err)
	}
	return &st
}

func TestReportFindsRunningNodeWithExpiredLease(t *testing.T) {
	f := newRun(t)
	expired := time.Now().Add(-time.Hour)
	f.withState(t, map[string]*store.NodeState{
		"1": {Status: plan.StatusRunning, Owner: "w1", LeaseUntil: expired, Attempts: 2},
	})

	run, stuck, err := Report(f.dir)
	if err != nil {
		t.Fatalf("Report: %v", err)
	}
	if run != "recovertest" {
		t.Errorf("run = %q, want recovertest", run)
	}
	if len(stuck) != 1 {
		t.Fatalf("stuck = %d entries, want 1: %+v", len(stuck), stuck)
	}
	got := stuck[0]
	if got.ID != "1" || !got.Expired || got.Owner != "w1" || got.Attempts != 2 {
		t.Errorf("stuck[0] = %+v, want id=1 expired=true owner=w1 attempts=2", got)
	}
	if got.Reason != reasonExpired {
		t.Errorf("reason = %q, want %q", got.Reason, reasonExpired)
	}
}

func TestReportReasonsDistinguishEvidence(t *testing.T) {
	now := time.Now()
	tests := []struct {
		name   string
		state  *store.NodeState
		want   string
		expiry bool
	}{
		{
			name:  "live lease",
			state: &store.NodeState{Status: plan.StatusRunning, Owner: "w1", LeaseUntil: now.Add(time.Hour)},
			want:  reasonLiveLease,
		},
		{
			name:  "no owner and no lease",
			state: &store.NodeState{Status: plan.StatusRunning},
			want:  reasonNoOwnerNoLease,
			// A zero lease is by definition not in the future, so the original
			// CLI also reported expired=true here. Preserved, not corrected.
			expiry: true,
		},
		{
			name:  "lease but no owner",
			state: &store.NodeState{Status: plan.StatusRunning, LeaseUntil: now.Add(time.Hour)},
			want:  reasonNoOwner,
		},
		{
			name:   "expired lease",
			state:  &store.NodeState{Status: plan.StatusRunning, Owner: "w1", LeaseUntil: now.Add(-time.Minute)},
			want:   reasonExpired,
			expiry: true,
		},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			f := newRun(t)
			f.withState(t, map[string]*store.NodeState{"1": tc.state})
			_, stuck, err := Report(f.dir)
			if err != nil {
				t.Fatalf("Report: %v", err)
			}
			if len(stuck) != 1 {
				t.Fatalf("stuck = %d entries, want 1", len(stuck))
			}
			if stuck[0].Reason != tc.want {
				t.Errorf("reason = %q, want %q", stuck[0].Reason, tc.want)
			}
			if stuck[0].Expired != tc.expiry {
				t.Errorf("expired = %v, want %v", stuck[0].Expired, tc.expiry)
			}
		})
	}
}

func TestReportSkipsNonRunningNodes(t *testing.T) {
	f := newRun(t)
	f.withState(t, map[string]*store.NodeState{
		"1": {Status: plan.StatusRunning, Owner: "w1", LeaseUntil: time.Now().Add(-time.Minute)},
		"2": {Status: plan.StatusDone},
		"3": {Status: plan.StatusFailed},
		"4": {Status: plan.StatusPending},
	})

	_, stuck, err := Report(f.dir)
	if err != nil {
		t.Fatalf("Report: %v", err)
	}
	if len(stuck) != 1 || stuck[0].ID != "1" {
		t.Fatalf("stuck = %+v, want only node 1", stuck)
	}
}

func TestReportIsDeterministicAcrossSeveralNodes(t *testing.T) {
	f := newRun(t)
	f.withState(t, map[string]*store.NodeState{
		"4": {Status: plan.StatusRunning, Owner: "w4", LeaseUntil: time.Now().Add(-time.Minute)},
		"1": {Status: plan.StatusRunning, Owner: "w1", LeaseUntil: time.Now().Add(-time.Minute)},
		"3": {Status: plan.StatusRunning, Owner: "w3", LeaseUntil: time.Now().Add(-time.Minute)},
		"2": {Status: plan.StatusRunning, Owner: "w2", LeaseUntil: time.Now().Add(-time.Minute)},
	})

	for i := 0; i < 3; i++ {
		_, stuck, err := Report(f.dir)
		if err != nil {
			t.Fatalf("Report: %v", err)
		}
		got := make([]string, 0, len(stuck))
		for _, s := range stuck {
			got = append(got, s.ID)
		}
		want := []string{"1", "2", "3", "4"}
		if len(got) != len(want) {
			t.Fatalf("ids = %v, want %v", got, want)
		}
		for j := range want {
			if got[j] != want[j] {
				t.Fatalf("iteration %d: ids = %v, want %v", i, got, want)
			}
		}
	}
}

func TestReportWithoutStateIsAnError(t *testing.T) {
	f := newRun(t)
	run, stuck, err := Report(f.dir)
	if err == nil {
		t.Fatalf("Report succeeded on a directory with no state.json (run=%q stuck=%+v)", run, stuck)
	}
	if !errors.Is(err, os.ErrNotExist) {
		t.Errorf("error = %v, want it to wrap os.ErrNotExist", err)
	}
}

func TestReclaimWithEmptyIDsReclaimsEveryStuckNode(t *testing.T) {
	f := newRun(t)
	f.withState(t, map[string]*store.NodeState{
		"1": {Status: plan.StatusRunning, Owner: "w1", LeaseUntil: time.Now().Add(-time.Minute), Attempts: 3},
		"2": {Status: plan.StatusRunning, Owner: "w2", LeaseUntil: time.Now().Add(time.Hour), Attempts: 1},
		"3": {Status: plan.StatusDone, Attempts: 2},
		"4": {Status: plan.StatusPending},
	})

	got, err := Reclaim(f.dir, nil)
	if err != nil {
		t.Fatalf("Reclaim: %v", err)
	}
	if len(got) != 2 || got[0] != "1" || got[1] != "2" {
		t.Fatalf("reclaimed = %v, want [1 2]", got)
	}

	st := f.readState(t)
	for _, id := range []string{"1", "2"} {
		ns := st.Nodes[id]
		if ns == nil {
			t.Fatalf("node %s missing from state", id)
		}
		if ns.Status != plan.StatusPending {
			t.Errorf("node %s status = %q, want pending", id, ns.Status)
		}
		if ns.Owner != "" {
			t.Errorf("node %s owner = %q, want empty", id, ns.Owner)
		}
		if !ns.LeaseUntil.IsZero() {
			t.Errorf("node %s lease = %v, want zero", id, ns.LeaseUntil)
		}
		if ns.LastError != reclaimError {
			t.Errorf("node %s last_error = %q, want %q", id, ns.LastError, reclaimError)
		}
	}
	// A reclaim must not buy free retries: the attempts already spent survive.
	if st.Nodes["1"].Attempts != 3 {
		t.Errorf("node 1 attempts = %d, want 3 (unchanged)", st.Nodes["1"].Attempts)
	}
	if st.Nodes["2"].Attempts != 1 {
		t.Errorf("node 2 attempts = %d, want 1 (unchanged)", st.Nodes["2"].Attempts)
	}
	// Nodes that were not running are untouched.
	if st.Nodes["3"].Status != plan.StatusDone || st.Nodes["3"].Attempts != 2 {
		t.Errorf("node 3 = %+v, want done with attempts 2", st.Nodes["3"])
	}
}

func TestReclaimWithExplicitIDReclaimsOnlyThatNode(t *testing.T) {
	f := newRun(t)
	f.withState(t, map[string]*store.NodeState{
		"1": {Status: plan.StatusRunning, Owner: "w1", LeaseUntil: time.Now().Add(-time.Minute)},
		"2": {Status: plan.StatusRunning, Owner: "w2", LeaseUntil: time.Now().Add(-time.Minute)},
	})

	got, err := Reclaim(f.dir, []string{"2"})
	if err != nil {
		t.Fatalf("Reclaim: %v", err)
	}
	if len(got) != 1 || got[0] != "2" {
		t.Fatalf("reclaimed = %v, want [2]", got)
	}

	st := f.readState(t)
	if st.Nodes["1"].Status != plan.StatusRunning {
		t.Errorf("node 1 status = %q, want still running", st.Nodes["1"].Status)
	}
	if st.Nodes["2"].Status != plan.StatusPending {
		t.Errorf("node 2 status = %q, want pending", st.Nodes["2"].Status)
	}
}

func TestReclaimOfNonRunningNodeIsANoOp(t *testing.T) {
	f := newRun(t)
	f.withState(t, map[string]*store.NodeState{
		"1": {Status: plan.StatusRunning, Owner: "w1", LeaseUntil: time.Now().Add(-time.Minute)},
		"2": {Status: plan.StatusDone},
	})

	got, err := Reclaim(f.dir, []string{"2"})
	if err != nil {
		t.Fatalf("Reclaim done node: %v", err)
	}
	if len(got) != 0 {
		t.Fatalf("reclaimed = %v, want none", got)
	}

	// Idempotency: reclaim everything, then reclaim again and get nothing new.
	if _, err := Reclaim(f.dir, nil); err != nil {
		t.Fatalf("Reclaim all: %v", err)
	}
	again, err := Reclaim(f.dir, nil)
	if err != nil {
		t.Fatalf("second Reclaim: %v", err)
	}
	if len(again) != 0 {
		t.Fatalf("second reclaim = %v, want none", again)
	}

	st := f.readState(t)
	if st.Nodes["2"].Status != plan.StatusDone {
		t.Errorf("node 2 status = %q, want done (untouched)", st.Nodes["2"].Status)
	}
}
