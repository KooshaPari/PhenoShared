package plan

import (
	"strings"
	"testing"
)

// replanBaseYAML is the plan every replan test starts from. It has three
// nodes: an intent, a spec that depends on it, and an implementation that
// depends on both. Every field that decides what "done" means is explicit, so
// a test can change exactly one thing and see exactly one change.
const replanBaseYAML = `
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

// replanNoThreeYAML is the base plan with node 3 dropped.
const replanNoThreeYAML = `
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

// replanWithFourYAML is the base plan with a new node appended.
const replanWithFourYAML = replanBaseYAML + `  - id: "4"
    kind: DOC
    title: "Write the docs"
    deps: ["3"]
`

// replanVariant rewrites one line of the base plan. Tests use it to change
// exactly one thing, so a failure names the rule that broke rather than the
// whole plan.
func replanVariant(t *testing.T, old, new string) string {
	t.Helper()
	if !strings.Contains(replanBaseYAML, old) {
		t.Fatalf("base plan does not contain %q", old)
	}
	return strings.Replace(replanBaseYAML, old, new, 1)
}

// changeFor returns the change recorded for one node id.
func changeFor(t *testing.T, d ReplanDiff, id string) NodeChange {
	t.Helper()
	for _, c := range d.Changes {
		if c.ID == id {
			return c
		}
	}
	t.Fatalf("no change recorded for node %q (got %+v)", id, d.Changes)
	return NodeChange{}
}

func TestDiffChangeKinds(t *testing.T) {
	cases := []struct {
		name string
		// new is the revised plan.
		new string
		// id is the node the case is about.
		id string
		// wantKind is the expected classification.
		wantKind ChangeKind
		// wantKeeps is the expected KeepsCompletion flag.
		wantKeeps bool
		// wantBlocking is whether the node must block the replan.
		wantBlocking bool
	}{
		{
			name:      "identical plan",
			new:       replanBaseYAML,
			id:        "2",
			wantKind:  ChangeUnchanged,
			wantKeeps: true,
		},
		{
			name:      "title only change keeps completion",
			new:       replanVariant(t, `title: "Write the spec"`, `title: "Write the specification"`),
			id:        "2",
			wantKind:  ChangeRenamedTitle,
			wantKeeps: true,
		},
		{
			name:         "artifact predicate change blocks",
			new:          replanVariant(t, "min_bytes: 400", "min_bytes: 800"),
			id:           "2",
			wantKind:     ChangeContractChanged,
			wantKeeps:    false,
			wantBlocking: true,
		},
		{
			name:         "check change blocks",
			new:          replanVariant(t, "        min_bytes: 400", "        min_bytes: 400\n    check: \"true\""),
			id:           "2",
			wantKind:     ChangeContractChanged,
			wantKeeps:    false,
			wantBlocking: true,
		},
		{
			name:         "kind change blocks",
			new:          replanVariant(t, "kind: SPEC", "kind: PLAN"),
			id:           "2",
			wantKind:     ChangeContractChanged,
			wantKeeps:    false,
			wantBlocking: true,
		},
		{
			name:         "role change blocks",
			new:          replanVariant(t, `title: "Write the spec"`, `title: "Write the spec"`+"\n    role: \"reviewer\""),
			id:           "2",
			wantKind:     ChangeContractChanged,
			wantKeeps:    false,
			wantBlocking: true,
		},
		{
			name:         "dep set change blocks",
			new:          replanVariant(t, `deps: ["1", "2"]`, `deps: ["2"]`),
			id:           "3",
			wantKind:     ChangeDepsChanged,
			wantKeeps:    false,
			wantBlocking: true,
		},
		{
			name:      "dep reorder that does not change the set keeps completion",
			new:       replanVariant(t, `deps: ["1", "2"]`, `deps: ["2", "1"]`),
			id:        "3",
			wantKind:  ChangeUnchanged,
			wantKeeps: true,
		},
		{
			name:         "removed node is reported but not blocking here",
			new:          replanNoThreeYAML,
			id:           "3",
			wantKind:     ChangeRemoved,
			wantKeeps:    false,
			wantBlocking: false,
		},
		{
			name:         "added node is never blocking",
			new:          replanWithFourYAML,
			id:           "4",
			wantKind:     ChangeAdded,
			wantKeeps:    false,
			wantBlocking: false,
		},
	}

	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			old := parsePlan(t, replanBaseYAML)
			updated := parsePlan(t, c.new)
			d := Diff(old, updated)

			got := changeFor(t, d, c.id)
			if got.Kind != c.wantKind {
				t.Errorf("node %s: kind = %q, want %q (detail %q)", c.id, got.Kind, c.wantKind, got.Detail)
			}
			if got.KeepsCompletion != c.wantKeeps {
				t.Errorf("node %s: KeepsCompletion = %v, want %v (detail %q)", c.id, got.KeepsCompletion, c.wantKeeps, got.Detail)
			}
			if blocking := containsID(d.Blocking, c.id); blocking != c.wantBlocking {
				t.Errorf("node %s: blocking = %v, want %v (blocking list %v)", c.id, blocking, c.wantBlocking, d.Blocking)
			}
			if d.Safe == c.wantBlocking {
				t.Errorf("Safe = %v, want %v when a node is blocking", d.Safe, !c.wantBlocking)
			}
		})
	}
}

func TestDiffIdenticalPlansAreSafe(t *testing.T) {
	old := parsePlan(t, replanBaseYAML)
	updated := parsePlan(t, replanBaseYAML)
	d := Diff(old, updated)

	if !d.Safe {
		t.Errorf("Safe = false for an unchanged plan, want true")
	}
	if len(d.Blocking) != 0 {
		t.Errorf("Blocking = %v, want empty", d.Blocking)
	}
	if len(d.Changes) != 3 {
		t.Fatalf("got %d changes, want 3 (one per node)", len(d.Changes))
	}
	for _, c := range d.Changes {
		if c.Kind != ChangeUnchanged {
			t.Errorf("node %s: kind = %q, want %q", c.ID, c.Kind, ChangeUnchanged)
		}
		if !c.KeepsCompletion {
			t.Errorf("node %s: KeepsCompletion = false, want true for an unchanged node", c.ID)
		}
	}
}

func TestDiffIsOrderedByID(t *testing.T) {
	old := parsePlan(t, replanBaseYAML)
	updated := parsePlan(t, replanWithFourYAML)
	d := Diff(old, updated)

	want := []string{"1", "2", "3", "4"}
	got := make([]string, 0, len(d.Changes))
	for _, c := range d.Changes {
		got = append(got, c.ID)
	}
	if strings.Join(got, ",") != strings.Join(want, ",") {
		t.Errorf("changes ordered %v, want %v", got, want)
	}
}

func TestDiffIsDeterministic(t *testing.T) {
	// The same pair of plans must always produce the same report, whatever
	// order the nodes were written in.
	old := parsePlan(t, replanBaseYAML)
	updated := parsePlan(t, replanWithFourYAML)

	first := Diff(old, updated)
	for i := 0; i < 5; i++ {
		again := Diff(old, updated)
		if len(again.Changes) != len(first.Changes) {
			t.Fatalf("change count differs between runs: %d vs %d", len(again.Changes), len(first.Changes))
		}
		for j := range first.Changes {
			if again.Changes[j] != first.Changes[j] {
				t.Fatalf("change %d differs between runs: %+v vs %+v", j, again.Changes[j], first.Changes[j])
			}
		}
	}
}

func TestAgainstDoneReportsRemovedVerifiedNode(t *testing.T) {
	old := parsePlan(t, replanBaseYAML)
	updated := parsePlan(t, replanNoThreeYAML)
	d := Diff(old, updated)

	// The removal itself is not blocking: Diff cannot see that node 3 was
	// ever verified. The caller decides, and this is the call that decides.
	got := d.AgainstDone([]string{"1", "2", "3"})
	if len(got) != 1 || got[0] != "3" {
		t.Fatalf("AgainstDone = %v, want [3]", got)
	}
}

func TestAgainstDoneKeepsUnchangedVerifiedNodes(t *testing.T) {
	old := parsePlan(t, replanBaseYAML)
	updated := parsePlan(t, replanVariant(t, `title: "Build it"`, `title: "Build the thing"`))
	d := Diff(old, updated)

	if got := d.AgainstDone([]string{"1", "2", "3"}); len(got) != 0 {
		t.Fatalf("AgainstDone = %v, want empty for a rename", got)
	}
}

func TestAgainstDoneReportsContractChange(t *testing.T) {
	old := parsePlan(t, replanBaseYAML)
	updated := parsePlan(t, replanVariant(t, "min_bytes: 400", "min_bytes: 800"))
	d := Diff(old, updated)

	got := d.AgainstDone([]string{"1", "2"})
	if len(got) != 1 || got[0] != "2" {
		t.Fatalf("AgainstDone = %v, want [2]", got)
	}
}

func TestAgainstDoneIgnoresUnknownAndDuplicateIDs(t *testing.T) {
	old := parsePlan(t, replanBaseYAML)
	updated := parsePlan(t, replanBaseYAML)
	d := Diff(old, updated)

	got := d.AgainstDone([]string{"1", "1", "", "2"})
	if len(got) != 0 {
		t.Fatalf("AgainstDone = %v, want empty for verified unchanged nodes", got)
	}
	// An id the diff knows nothing about was verified under a plan this
	// comparison does not cover, so it must not be silently dropped.
	got = d.AgainstDone([]string{"9"})
	if len(got) != 1 || got[0] != "9" {
		t.Fatalf("AgainstDone = %v, want [9]", got)
	}
}

func TestDiffToleratesNilPlans(t *testing.T) {
	d := Diff(nil, nil)
	if !d.Safe {
		t.Errorf("Safe = false for two empty plans, want true")
	}
	if len(d.Changes) != 0 {
		t.Errorf("got %d changes for two nil plans, want 0", len(d.Changes))
	}
	if got := d.AgainstDone([]string{"1"}); len(got) != 1 || got[0] != "1" {
		t.Errorf("AgainstDone = %v, want [1]", got)
	}
}

// contains reports whether a string slice holds a value.
func containsID(list []string, want string) bool {
	for _, v := range list {
		if v == want {
			return true
		}
	}
	return false
}
