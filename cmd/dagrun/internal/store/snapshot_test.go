package store

import (
	"encoding/json"
	"errors"
	"os"
	"strconv"
	"testing"

	"github.com/KooshaPari/dagrun/internal/plan"
)

// readStateBytes returns the raw on-disk document.
func readStateBytes(t *testing.T, st *Store) []byte {
	t.Helper()
	raw, err := os.ReadFile(st.statePath())
	if err != nil {
		t.Fatalf("read state: %v", err)
	}
	return raw
}

// planOnlyStore builds a Store handle for a run directory that was planned but
// never opened for execution, so no state.json has been written. Open would
// create one, which is exactly what this case must not rely on.
func planOnlyStore(t *testing.T, dir string) *Store {
	t.Helper()
	p, err := plan.Parse([]byte(testPlan))
	if err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	p.Root = dir
	return &Store{dir: dir, root: dir, plan: p, planHash: "planned-never-run"}
}

// A snapshot is a read: it must not rewrite the document or move UpdatedAt.
// Before the fix Snapshot went through With, so both of these advanced on every
// call and a `status --watch` monitor sat on the write path.
func TestSnapshotDoesNotWriteState(t *testing.T) {
	st := newStore(t, t.TempDir(), 0)

	before := readStateBytes(t, st)
	first, err := st.Snapshot()
	if err != nil {
		t.Fatalf("first snapshot: %v", err)
	}
	second, err := st.Snapshot()
	if err != nil {
		t.Fatalf("second snapshot: %v", err)
	}

	after := readStateBytes(t, st)
	if string(before) != string(after) {
		t.Fatalf("Snapshot rewrote state.json\nbefore: %s\nafter:  %s", before, after)
	}
	if !first.UpdatedAt.Equal(second.UpdatedAt) {
		t.Fatalf("Snapshot advanced UpdatedAt: %s -> %s", first.UpdatedAt, second.UpdatedAt)
	}
	var doc State
	if err := json.Unmarshal(after, &doc); err != nil {
		t.Fatalf("unmarshal state: %v", err)
	}
	if !doc.UpdatedAt.Equal(second.UpdatedAt) {
		t.Fatalf("on-disk UpdatedAt %s != snapshot %s", doc.UpdatedAt, second.UpdatedAt)
	}
}

// The returned state is still a deep copy: mutating it must not touch the store.
func TestSnapshotReturnsAnIndependentCopy(t *testing.T) {
	st := newStore(t, t.TempDir(), 0)

	snap, err := st.Snapshot()
	if err != nil {
		t.Fatalf("snapshot: %v", err)
	}
	snap.Nodes["1"].Status = plan.StatusDone
	snap.Nodes["injected"] = &NodeState{Status: plan.StatusPending}
	delete(snap.Nodes, "2")
	snap.Expanded["x"] = true
	snap.Run = "mutated"

	onDisk, err := st.Snapshot()
	if err != nil {
		t.Fatalf("re-read snapshot: %v", err)
	}
	if onDisk.Nodes["1"].Status != plan.StatusPending {
		t.Fatalf("mutating the snapshot changed the store: node 1 = %q", onDisk.Nodes["1"].Status)
	}
	if _, ok := onDisk.Nodes["injected"]; ok {
		t.Fatal("mutating the snapshot added a node to the store")
	}
	if _, ok := onDisk.Nodes["2"]; !ok {
		t.Fatal("mutating the snapshot removed a node from the store")
	}
	if onDisk.Expanded["x"] {
		t.Fatal("mutating the snapshot changed the store's Expanded map")
	}
	if onDisk.Run == "mutated" {
		t.Fatal("mutating the snapshot changed the store's Run")
	}
}

// A planned-but-unrun directory has no state.json; Snapshot must still return a
// usable all-pending state rather than an error.
func TestSnapshotWithoutStateFileReturnsPendingNodes(t *testing.T) {
	dir := t.TempDir()
	st := planOnlyStore(t, dir)

	snap, err := st.Snapshot()
	if err != nil {
		t.Fatalf("snapshot: %v", err)
	}
	if len(snap.Nodes) != len(st.plan.Nodes) {
		t.Fatalf("snapshot has %d nodes, plan has %d", len(snap.Nodes), len(st.plan.Nodes))
	}
	for _, n := range st.plan.Nodes {
		ns, ok := snap.Nodes[n.ID]
		if !ok {
			t.Fatalf("node %q missing from snapshot", n.ID)
		}
		if ns.Status != plan.StatusPending {
			t.Fatalf("node %q status = %q, want %q", n.ID, ns.Status, plan.StatusPending)
		}
	}
	if _, err := os.Stat(st.statePath()); !os.IsNotExist(err) {
		t.Fatalf("Snapshot created state.json on a read (stat err = %v)", err)
	}
}

// A state written by a newer binary is refused, not half-read.
func TestSnapshotRefusesNewerSchema(t *testing.T) {
	dir := t.TempDir()
	st := planOnlyStore(t, dir)
	doc := []byte(`{"version":` + strconv.Itoa(SchemaVersion+1) + `,"run":"future","nodes":{}}`)
	if err := os.WriteFile(st.statePath(), doc, 0o644); err != nil {
		t.Fatal(err)
	}

	snap, err := st.Snapshot()
	if err == nil {
		t.Fatalf("expected refusal, got snapshot %+v", snap)
	}
	if !errors.Is(err, ErrStateTooNew) {
		t.Fatalf("error = %v, want ErrStateTooNew", err)
	}
	if snap != nil {
		t.Fatalf("refused snapshot still returned state: %+v", snap)
	}
}

// Guard: writes still persist through With, so the read fix did not neuter the
// write path.
func TestWithStillPersistsAfterReadFix(t *testing.T) {
	st := newStore(t, t.TempDir(), 0)
	before, err := st.Snapshot()
	if err != nil {
		t.Fatalf("snapshot: %v", err)
	}

	if err := st.With(func(s *State) error {
		s.Nodes["1"].Status = plan.StatusDone
		return nil
	}); err != nil {
		t.Fatalf("with: %v", err)
	}

	after, err := st.Snapshot()
	if err != nil {
		t.Fatalf("snapshot after write: %v", err)
	}
	if after.Nodes["1"].Status != plan.StatusDone {
		t.Fatalf("node 1 status = %q, want %q", after.Nodes["1"].Status, plan.StatusDone)
	}
	if !after.UpdatedAt.After(before.UpdatedAt) {
		t.Fatalf("With did not advance UpdatedAt: %s -> %s", before.UpdatedAt, after.UpdatedAt)
	}

	var doc State
	if err := json.Unmarshal(readStateBytes(t, st), &doc); err != nil {
		t.Fatalf("unmarshal state: %v", err)
	}
	if doc.Nodes["1"].Status != plan.StatusDone {
		t.Fatalf("on-disk node 1 status = %q, want %q", doc.Nodes["1"].Status, plan.StatusDone)
	}
}
