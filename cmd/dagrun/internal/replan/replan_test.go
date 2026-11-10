package replan

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// basePlan is the plan every replan test starts from. It has three nodes, each
// with an explicit artifact contract, so a test can change exactly one thing and
// see exactly one consequence.
const basePlan = `
version: 1
run: replan
nodes:
  - id: "1"
    kind: INTENT
    title: "Frame the work"
  - id: "2"
    kind: SPEC
    title: "Write the spec"
    deps: ["1"]
    artifacts:
      - path: artifacts/SPEC.md
        min_bytes: 400
  - id: "3"
    kind: IMPL
    title: "Build it"
    deps: ["1", "2"]
    artifacts:
      - path: artifacts/IMPL.md
        min_bytes: 200
`

// noThreePlan is the base plan with node 3 removed.
const noThreePlan = `
version: 1
run: replan
nodes:
  - id: "1"
    kind: INTENT
    title: "Frame the work"
  - id: "2"
    kind: SPEC
    title: "Write the spec"
    deps: ["1"]
    artifacts:
      - path: artifacts/SPEC.md
        min_bytes: 400
`

// variant rewrites one line of the base plan so a case changes one thing.
func variant(t *testing.T, old, new string) string {
	t.Helper()
	if !strings.Contains(basePlan, old) {
		t.Fatalf("base plan does not contain %q", old)
	}
	return strings.Replace(basePlan, old, new, 1)
}

// seedRun installs the base plan and marks every node done with a distinct
// attempt count, so a test can tell "kept" from "reset" by the number alone.
func seedRun(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	raw := []byte(basePlan)
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), raw, 0o644); err != nil {
		t.Fatal(err)
	}
	p, err := plan.Parse(raw)
	if err != nil {
		t.Fatal(err)
	}
	p.Root = dir
	st, err := store.Open(dir, p, raw, false)
	if err != nil {
		t.Fatal(err)
	}
	attempts := map[string]int{"1": 2, "2": 3, "3": 1}
	if err := st.With(func(s *store.State) error {
		for id, n := range attempts {
			prev, ok := s.Nodes[id]
			if !ok {
				return fmt.Errorf("seeded plan has no node %s", id)
			}
			prev.Status = plan.StatusDone
			prev.Attempts = n
		}
		return nil
	}); err != nil {
		t.Fatal(err)
	}
	return dir
}

// readState decodes state.json directly; it is a test assertion, not a store
// operation, so it must not go through the lock.
func readState(t *testing.T, dir string) *store.State {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join(dir, "state.json"))
	if err != nil {
		t.Fatal(err)
	}
	var st store.State
	if err := json.Unmarshal(raw, &st); err != nil {
		t.Fatal(err)
	}
	return &st
}

func readFile(t *testing.T, path string) string {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}

func ids(list []string) string { return strings.Join(list, ",") }

func TestApply(t *testing.T) {
	type want struct {
		// status is the expected status for every surviving node.
		status map[string]string
		// attempts is the expected attempt count for every surviving node.
		attempts map[string]int
		// absent lists ids that must not exist in state after the apply.
		absent []string
		// kept and discarded are the expected Result slices, comma-joined.
		kept      string
		discarded string
	}

	cases := []struct {
		name      string
		revised   string
		force     bool
		wantErr   string
		wantAfter want
	}{
		{
			name:    "identical plan keeps every completion",
			revised: basePlan,
			wantAfter: want{
				status:    map[string]string{"1": plan.StatusDone, "2": plan.StatusDone, "3": plan.StatusDone},
				attempts:  map[string]int{"1": 2, "2": 3, "3": 1},
				kept:      "1,2,3",
				discarded: "",
			},
		},
		{
			name:    "changed artifact contract invalidates that node only",
			revised: variant(t, "min_bytes: 400", "min_bytes: 800"),
			force:   true,
			wantAfter: want{
				status:    map[string]string{"1": plan.StatusDone, "2": plan.StatusPending, "3": plan.StatusDone},
				attempts:  map[string]int{"1": 2, "2": 0, "3": 1},
				kept:      "1,3",
				discarded: "2",
			},
		},
		{
			name:    "title-only change keeps the completion",
			revised: variant(t, `title: "Write the spec"`, `title: "Write the specification"`),
			wantAfter: want{
				status:    map[string]string{"1": plan.StatusDone, "2": plan.StatusDone, "3": plan.StatusDone},
				attempts:  map[string]int{"1": 2, "2": 3, "3": 1},
				kept:      "1,2,3",
				discarded: "",
			},
		},
		{
			name:    "force migrates a changed contract, keeping other completions",
			revised: variant(t, "min_bytes: 400", "min_bytes: 800"),
			force:   true,
			wantAfter: want{
				status:    map[string]string{"1": plan.StatusDone, "2": plan.StatusPending, "3": plan.StatusDone},
				attempts:  map[string]int{"1": 2, "2": 0, "3": 1},
				kept:      "1,3",
				discarded: "2",
			},
		},
		{
			name:    "removed node is dropped from state",
			revised: noThreePlan,
			force:   true,
			wantAfter: want{
				status:    map[string]string{"1": plan.StatusDone, "2": plan.StatusDone},
				attempts:  map[string]int{"1": 2, "2": 3},
				absent:    []string{"3"},
				kept:      "1,2",
				discarded: "3",
			},
		},
		{
			name:    "unforced discard is refused and writes nothing",
			revised: variant(t, "min_bytes: 400", "min_bytes: 800"),
			force:   false,
			wantErr: "2",
			wantAfter: want{
				status:    map[string]string{"1": plan.StatusDone, "2": plan.StatusDone, "3": plan.StatusDone},
				attempts:  map[string]int{"1": 2, "2": 3, "3": 1},
				kept:      "",
				discarded: "",
			},
		},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			dir := seedRun(t)
			planPath := filepath.Join(dir, "run.yaml")
			statePath := filepath.Join(dir, "state.json")
			beforePlan := readFile(t, planPath)
			beforeState := readFile(t, statePath)

			revisedRaw := []byte(c.revised)
			revised, err := plan.Parse(revisedRaw)
			if err != nil {
				t.Fatal(err)
			}

			res, err := Apply(dir, revised, revisedRaw, c.force)
			if c.wantErr != "" {
				if err == nil {
					t.Fatalf("Apply succeeded, want an error mentioning %q", c.wantErr)
				}
				if !strings.Contains(err.Error(), c.wantErr) {
					t.Fatalf("error = %q, want it to name %q", err, c.wantErr)
				}
				// A refusal must leave both documents exactly as they were.
				if got := readFile(t, planPath); got != beforePlan {
					t.Errorf("run.yaml changed after a refused apply")
				}
				if got := readFile(t, statePath); got != beforeState {
					t.Errorf("state.json changed after a refused apply")
				}
			} else {
				if err != nil {
					t.Fatalf("Apply: %v", err)
				}
				if got := ids(res.Kept); got != c.wantAfter.kept {
					t.Errorf("Kept = %q, want %q", got, c.wantAfter.kept)
				}
				if got := ids(res.Discarded); got != c.wantAfter.discarded {
					t.Errorf("Discarded = %q, want %q", got, c.wantAfter.discarded)
				}
			}

			st := readState(t, dir)
			for id, wantStatus := range c.wantAfter.status {
				ns, ok := st.Nodes[id]
				if !ok {
					t.Errorf("node %s missing from state", id)
					continue
				}
				if ns.Status != wantStatus {
					t.Errorf("node %s: status = %q, want %q", id, ns.Status, wantStatus)
				}
				if got, want := ns.Attempts, c.wantAfter.attempts[id]; got != want {
					t.Errorf("node %s: attempts = %d, want %d", id, got, want)
				}
			}
			for _, id := range c.wantAfter.absent {
				if _, ok := st.Nodes[id]; ok {
					t.Errorf("node %s should have been dropped from state", id)
				}
			}
		})
	}
}

// TestApplyLeavesReopenableState is the whole reason the write order matters: a
// successful apply must leave a directory store.Open accepts under the NEW plan.
func TestApplyLeavesReopenableState(t *testing.T) {
	dir := seedRun(t)
	revisedRaw := []byte(variant(t, "min_bytes: 400", "min_bytes: 800"))
	revised, err := plan.Parse(revisedRaw)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := Apply(dir, revised, revisedRaw, true); err != nil {
		t.Fatalf("Apply: %v", err)
	}

	// state.json now records the hash of the new bytes, so opening against the
	// new plan must not report "plan changed".
	revised.Root = dir
	if _, err := store.Open(dir, revised, revisedRaw, false); err != nil {
		t.Fatalf("store.Open after Apply: %v", err)
	}

	// The old plan must now be the one that is refused: that is the crash-safety
	// property, not a regression.
	oldRaw := []byte(basePlan)
	oldPlan, err := plan.Parse(oldRaw)
	if err != nil {
		t.Fatal(err)
	}
	oldPlan.Root = dir
	if _, err := store.Open(dir, oldPlan, oldRaw, false); err == nil {
		t.Fatal("store.Open accepted the pre-replan plan, want a hash-mismatch refusal")
	}
}

// TestApplyClearsDynamicAndExpanded guards the fields that would otherwise
// survive a revision and describe nodes the new plan no longer has.
func TestApplyClearsDynamicAndExpanded(t *testing.T) {
	dir := seedRun(t)
	raw := []byte(basePlan)
	p, err := plan.Parse(raw)
	if err != nil {
		t.Fatal(err)
	}
	p.Root = dir
	st, err := store.Open(dir, p, raw, false)
	if err != nil {
		t.Fatal(err)
	}
	if err := st.With(func(s *store.State) error {
		s.Dynamic["dyn"] = &plan.Node{ID: "dyn", Kind: "IMPL"}
		s.Expanded["1"] = true
		return nil
	}); err != nil {
		t.Fatal(err)
	}

	if _, err := Apply(dir, p, raw, false); err != nil {
		t.Fatalf("Apply: %v", err)
	}
	after := readState(t, dir)
	if len(after.Dynamic) != 0 {
		t.Errorf("Dynamic = %v, want empty", after.Dynamic)
	}
	if len(after.Expanded) != 0 {
		t.Errorf("Expanded = %v, want empty", after.Expanded)
	}
}
