package verify

import (
	"context"
	"os"
	"path/filepath"
	"testing"

	"github.com/KooshaPari/dagrun/internal/plan"
)

// Satisfied is the scheduler's cheap pre-filter. It must evaluate artifacts
// only: the node's check is owned by PlanNode, which produces the single
// authoritative verdict. Running the check twice (once here, once in PlanNode)
// is what made adoption cost ~2x the check.
//
// The check in this test is both failing and has a visible side effect, so the
// assertion is positive: if Satisfied never runs it, the marker file cannot
// exist afterwards.
func TestSatisfiedNeverExecutesTheCheck(t *testing.T) {
	root := t.TempDir()
	write(t, root, "out/report.txt", "body that satisfies the declared artifact")

	marker := filepath.Join(root, "check-ran.txt")
	n := &plan.Node{
		ID:        "x",
		Kind:      "IMPL",
		Artifacts: []plan.Artifact{{Path: "out/report.txt"}},
		Check:     "printf ran >> check-ran.txt; exit 1",
	}

	if !Satisfied(context.Background(), root, n) {
		t.Fatal("Satisfied = false; the artifact is present and the check is not its business")
	}
	if _, err := os.Stat(marker); !os.IsNotExist(err) {
		t.Fatalf("check ran inside Satisfied: %s exists (err=%v); artifacts-only was not honoured", marker, err)
	}

	// The authoritative verdict does run the check, and it must fail: that is
	// how adopt still refuses a node whose check is red.
	rep := PlanNode(context.Background(), root, n, nil)
	if rep.OK {
		t.Fatalf("PlanNode accepted a failing check: %+v", rep)
	}
	if rep.Check == nil || rep.Check.OK {
		t.Fatalf("PlanNode check = %+v, want a failing CheckResult", rep.Check)
	}
	if _, err := os.Stat(marker); err != nil {
		t.Fatalf("PlanNode did not run the check: %v", err)
	}
}

func TestSatisfiedArtifactMatrix(t *testing.T) {
	root := t.TempDir()
	write(t, root, "artifacts/present.md", "a present artifact with real body text")

	cases := []struct {
		name string
		node *plan.Node
		want bool
	}{
		{
			name: "artifact present",
			node: &plan.Node{ID: "a", Kind: "DOC",
				Artifacts: []plan.Artifact{{Path: "artifacts/present.md"}},
				Check:     "exit 1"},
			want: true,
		},
		{
			name: "artifact missing",
			node: &plan.Node{ID: "b", Kind: "DOC",
				Artifacts: []plan.Artifact{{Path: "artifacts/absent.md"}}},
			want: false,
		},
		{
			name: "artifact fails its predicate",
			node: &plan.Node{ID: "c", Kind: "DOC",
				Artifacts: []plan.Artifact{{Path: "artifacts/present.md", MinBytes: 1 << 20}}},
			want: false,
		},
		{
			name: "no artifacts at all",
			node: &plan.Node{ID: "d", Kind: "IMPL", Check: "true"},
			want: false,
		},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := Satisfied(context.Background(), root, c.node); got != c.want {
				t.Fatalf("Satisfied = %v, want %v", got, c.want)
			}
		})
	}
}
