package agileplus

import (
	"bytes"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/KooshaPari/dagrun/internal/export"
	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

const bundleJSON = `{
  "projects": [
    {
      "slug": "demo",
      "name": "demo",
      "features": [
        {
          "friendly_name": "demo-run",
          "slug": "demo-run",
          "spec_content": "# Specification: demo",
          "state": "doing",
          "work_packages": [
            {"sequence": 1, "title": "Freeze scope", "state": "done", "file_scope": ["artifacts/INTENT.md"]},
            {"sequence": 2, "title": "Write the spec", "state": "planned",
             "acceptance_criteria": "test -s artifacts/SPEC.md", "file_scope": ["artifacts/SPEC.md"]},
            {"sequence": 3, "title": "Prove the spec", "state": "planned",
             "acceptance_criteria": "go test ./...", "depends_on_sequences": [2]}
          ]
        }
      ]
    }
  ],
  "modules": [], "features": [], "cycles": []
}`

// The reader must mirror the emitter's field names. A round trip that silently
// reads nothing is worse than one that errors, so this compares the JSON tags.
func TestBundleShapeMatchesTheExporter(t *testing.T) {
	// Build a real bundle through export, then parse it back. If the field
	// names drifted, the parse yields empty structs and the assertions fail.
	p, err := plan.Parse([]byte(`version: 1
run: demo-run
nodes:
  - id: "1"
    kind: IMPL
    title: one
    artifacts: [{path: a.md, min_bytes: 1}]
`))
	if err != nil {
		t.Fatal(err)
	}
	raw, err := export.AgilePlus(export.Input{Plan: p, State: &store.State{Nodes: map[string]*store.NodeState{}}})
	if err != nil {
		t.Fatal(err)
	}
	b, err := Parse(bytes.NewReader(raw))
	if err != nil {
		t.Fatalf("the exporter's own output does not parse: %v", err)
	}
	if len(b.Projects) != 1 || len(b.Projects[0].Features) != 1 {
		t.Fatalf("export -> parse lost the structure: %+v", b)
	}
	f := b.Projects[0].Features[0]
	if f.Slug != "demo-run" {
		t.Errorf("feature slug = %q, want demo-run", f.Slug)
	}
	if len(f.WorkPackages) != 1 {
		t.Fatalf("work packages = %d, want 1", len(f.WorkPackages))
	}
	if f.WorkPackages[0].FileScope[0] != "a.md" {
		t.Errorf("file scope = %v, want [a.md]", f.WorkPackages[0].FileScope)
	}
}

func TestParseRejectsMalformedJSON(t *testing.T) {
	if _, err := Parse(strings.NewReader(`{"projects": [`)); err == nil {
		t.Fatal("expected an error for truncated JSON")
	}
}

func TestToPlanMapsWorkPackages(t *testing.T) {
	b, err := Parse(strings.NewReader(bundleJSON))
	if err != nil {
		t.Fatal(err)
	}
	p, unmapped, err := ToPlan(b)
	if err != nil {
		t.Fatal(err)
	}
	if p.Run != "demo-run" {
		t.Errorf("run = %q, want demo-run", p.Run)
	}
	if len(p.Nodes) != 3 {
		t.Fatalf("nodes = %d, want 3", len(p.Nodes))
	}

	byID := map[string]*plan.Node{}
	for _, n := range p.Nodes {
		byID[n.ID] = n
	}
	if _, ok := byID["1"]; !ok {
		t.Errorf("missing node 1; ids are %v", ids(p))
	}
	if got := byID["2"].Check; got != "test -s artifacts/SPEC.md" {
		t.Errorf("node 2 check = %q", got)
	}
	if len(byID["3"].Deps) != 1 || byID["3"].Deps[0] != "2" {
		t.Errorf("node 3 deps = %v, want [2]", byID["3"].Deps)
	}
	// Sequence 1 was already finished upstream, so it must not be re-run.
	if !byID["1"].Optional {
		t.Error("a work package AgilePlus considers done must be imported as optional")
	}
	// Work package 1 has no acceptance criteria at all, so the only thing
	// reported about it is the predicate loss that comes from file_scope being
	// the only artifact-shaped field in an ImportBundle.
	for _, u := range unmapped {
		if u.Sequence == 1 && !strings.Contains(u.Reason, "predicates") {
			t.Errorf("work package 1 reported something unexpected: %s", u.Reason)
		}
	}
	// And the artifact paths it did carry are restored, so a second export is
	// not empty.
	if len(byID["1"].Artifacts) != 1 || byID["1"].Artifacts[0].Path != "artifacts/INTENT.md" {
		t.Errorf("node 1 artifacts = %+v, want the INTENT.md path restored", byID["1"].Artifacts)
	}
}

// Prose acceptance criteria must not become a shell command. Putting prose in
// `check` makes every imported node fail on a shell syntax error, which looks
// like the work is broken when the import is what was wrong.
func TestProseAcceptanceCriteriaIsReportedNotInvented(t *testing.T) {
	body := `{"projects":[{"slug":"p","name":"p","features":[{"slug":"f","work_packages":[
	  {"sequence":1,"title":"Do the thing","acceptance_criteria":"The thing works and looks nice"}
	]}]}]}`
	b, err := Parse(strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	p, unmapped, err := ToPlan(b)
	if err != nil {
		t.Fatal(err)
	}
	if got := p.Nodes[0].Check; got != "" {
		t.Errorf("prose became a check command: %q", got)
	}
	if len(unmapped) != 1 {
		t.Fatalf("unmapped = %v, want one entry for the prose criteria", unmapped)
	}
	if !strings.Contains(unmapped[0].Reason, "prose") {
		t.Errorf("reason does not explain itself: %q", unmapped[0].Reason)
	}
	// And no artifact was invented: the node has no way to verify, which the
	// caller can see and decide about.
	if len(p.Nodes[0].Artifacts) != 0 {
		t.Errorf("an artifact contract was invented: %+v", p.Nodes[0].Artifacts)
	}
}

func TestDependencyOnAMissingSequenceIsReported(t *testing.T) {
	body := `{"projects":[{"slug":"p","name":"p","features":[{"slug":"f","work_packages":[
	  {"sequence":1,"title":"a","depends_on_sequences":[7]}
	]}]}]}`
	b, err := Parse(strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	_, unmapped, err := ToPlan(b)
	if err != nil {
		t.Fatal(err)
	}
	found := false
	for _, u := range unmapped {
		if strings.Contains(u.Reason, "sequence 7") {
			found = true
		}
	}
	if !found {
		t.Fatalf("a forward reference to a missing sequence was dropped silently: %v", unmapped)
	}
}

func TestNegativeSequenceIsAnError(t *testing.T) {
	body := `{"projects":[{"slug":"p","name":"p","features":[{"slug":"f","work_packages":[
	  {"sequence":-1,"title":"a"}
	]}]}]}`
	b, err := Parse(strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	if _, _, err := ToPlan(b); err == nil {
		t.Fatal("expected an error for a negative sequence")
	}
}

func TestToPlanRejectsAnEmptyBundle(t *testing.T) {
	if _, _, err := ToPlan(&Bundle{}); err == nil {
		t.Fatal("expected an error for a bundle with no projects")
	}
	b := &Bundle{Projects: []Project{{Slug: "p", Features: []Feature{{Slug: "f"}}}}}
	if _, _, err := ToPlan(b); err == nil {
		t.Fatal("expected an error for a feature with no work packages")
	}
}

// The round trip that matters: export -> parse -> plan -> export preserves the
// structure. Slugs, sequences, titles and file scopes must survive.
func TestRoundTripPreservesStructure(t *testing.T) {
	src, err := plan.Parse([]byte(`version: 1
run: rt
nodes:
  - id: "1"
    kind: IMPL
    title: first
    artifacts: [{path: alpha.go, min_bytes: 1}]
  - id: "2"
    kind: IMPL
    title: second
    deps: ["1"]
    artifacts: [{path: beta.go, min_bytes: 1}]
`))
	if err != nil {
		t.Fatal(err)
	}
	first, err := export.AgilePlus(export.Input{Plan: src, State: &store.State{Nodes: map[string]*store.NodeState{}}})
	if err != nil {
		t.Fatal(err)
	}
	b, err := Parse(bytes.NewReader(first))
	if err != nil {
		t.Fatal(err)
	}
	re, _, err := ToPlan(b)
	if err != nil {
		t.Fatal(err)
	}
	second, err := export.AgilePlus(export.Input{Plan: re, State: &store.State{Nodes: map[string]*store.NodeState{}}})
	if err != nil {
		t.Fatal(err)
	}

	b1, err := Parse(bytes.NewReader(first))
	if err != nil {
		t.Fatal(err)
	}
	b2, err := Parse(bytes.NewReader(second))
	if err != nil {
		t.Fatal(err)
	}
	if len(b1.Projects) != 1 || len(b2.Projects) != 1 {
		t.Fatalf("project count changed across the round trip")
	}
	f1 := b1.Projects[0].Features[0]
	f2 := b2.Projects[0].Features[0]

	if f1.Slug != f2.Slug {
		t.Errorf("feature slug %q -> %q", f1.Slug, f2.Slug)
	}
	if len(f1.WorkPackages) != len(f2.WorkPackages) {
		t.Fatalf("work package count %d -> %d", len(f1.WorkPackages), len(f2.WorkPackages))
	}
	for i := range f1.WorkPackages {
		a, b := f1.WorkPackages[i], f2.WorkPackages[i]
		if a.Sequence != b.Sequence || a.Title != b.Title {
			t.Errorf("work package %d changed: %+v -> %+v", i, a, b)
		}
		if !reflect.DeepEqual(a.FileScope, b.FileScope) {
			t.Errorf("work package %d file scope %v -> %v", i, a.FileScope, b.FileScope)
		}
		if !reflect.DeepEqual(a.DependsOnSequences, b.DependsOnSequences) {
			t.Errorf("work package %d deps %v -> %v", i, a.DependsOnSequences, b.DependsOnSequences)
		}
	}
}

func TestIDMapPersistsAndRoundTrips(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "agileplus.map.json")

	m := NewIDMap()
	m.Set("f", 1, "1")
	m.Set("f", 2, "2")
	if err := m.Save(path); err != nil {
		t.Fatal(err)
	}

	got, err := LoadIDMap(path)
	if err != nil {
		t.Fatal(err)
	}
	for seq, want := range map[int]string{1: "1", 2: "2"} {
		id, ok := got.Resolve("f", seq)
		if !ok || id != want {
			t.Errorf("Resolve(f,%d) = %q,%v want %q", seq, id, ok, want)
		}
	}
}

// The first import has nothing to load. A missing map is empty, not an error.
func TestLoadIDMapMissingFileIsEmpty(t *testing.T) {
	m, err := LoadIDMap(filepath.Join(t.TempDir(), "absent.json"))
	if err != nil {
		t.Fatalf("a missing map must not be an error: %v", err)
	}
	if len(m.Nodes) != 0 {
		t.Errorf("got %d entries from an absent file", len(m.Nodes))
	}
	if _, ok := m.Resolve("f", 1); ok {
		t.Error("an absent map resolved a key")
	}
}

func TestConflictsReportsAChangedContract(t *testing.T) {
	existing := mustPlan(t, `version: 1
run: r
nodes:
  - id: "1"
    kind: IMPL
    title: a
    artifacts: [{path: x.go, min_bytes: 1}]
    check: "true"
`)
	incoming := mustPlan(t, `version: 1
run: r
nodes:
  - id: "1"
    kind: IMPL
    title: a
    artifacts: [{path: x.go, min_bytes: 1}]
    check: "go build ./..."
`)
	got := Conflicts(existing, incoming, nil)
	if len(got) != 1 {
		t.Fatalf("conflicts = %+v, want one", got)
	}
	if got[0].Kind != "contract_changed" || !strings.Contains(got[0].Detail, "check") {
		t.Errorf("conflict = %+v, want a contract_changed on the check", got[0])
	}
}

func TestConflictsIsSilentWhenNothingChanged(t *testing.T) {
	same := `version: 1
run: r
nodes:
  - id: "1"
    kind: IMPL
    title: a
    artifacts: [{path: x.go, min_bytes: 1}]
`
	if got := Conflicts(mustPlan(t, same), mustPlan(t, same), nil); len(got) != 0 {
		t.Fatalf("a no-op round trip reported conflicts: %+v", got)
	}
}

func TestConflictsReportsARemovedMappedNode(t *testing.T) {
	existing := mustPlan(t, `version: 1
run: r
nodes:
  - id: "1"
    kind: IMPL
    title: a
    artifacts: [{path: x.go, min_bytes: 1}]
  - id: "2"
    kind: IMPL
    title: b
    artifacts: [{path: y.go, min_bytes: 1}]
`)
	incoming := mustPlan(t, `version: 1
run: r
nodes:
  - id: "1"
    kind: IMPL
    title: a
    artifacts: [{path: x.go, min_bytes: 1}]
`)
	m := NewIDMap()
	m.Set("r", 1, "1")
	m.Set("r", 2, "2")

	got := Conflicts(existing, incoming, m)
	if len(got) != 1 || got[0].Kind != "node_removed" || got[0].NodeID != "2" {
		t.Fatalf("conflicts = %+v, want one node_removed for 2", got)
	}
}

// An unmapped node is not a removal: it may belong to a different feature.
func TestConflictsDoesNotInventRemovals(t *testing.T) {
	existing := mustPlan(t, `version: 1
run: r
nodes:
  - id: "1"
    kind: IMPL
    title: a
    artifacts: [{path: x.go, min_bytes: 1}]
  - id: "9"
    kind: IMPL
    title: unrelated
    artifacts: [{path: z.go, min_bytes: 1}]
`)
	incoming := mustPlan(t, `version: 1
run: r
nodes:
  - id: "1"
    kind: IMPL
    title: a
    artifacts: [{path: x.go, min_bytes: 1}]
`)
	m := NewIDMap()
	m.Set("r", 1, "1")

	if got := Conflicts(existing, incoming, m); len(got) != 0 {
		t.Fatalf("an unrecorded node was reported as removed: %+v", got)
	}
}

func TestParseFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "bundle.json")
	if err := os.WriteFile(path, []byte(bundleJSON), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := ParseFile(path); err != nil {
		t.Fatal(err)
	}
	if _, err := ParseFile(filepath.Join(dir, "absent.json")); err == nil {
		t.Fatal("expected an error for a missing file")
	}
}

// Node ids must order correctly under plan.Less, which is the only ordering the
// tool uses. Zero-padding is not needed for that and is deliberately absent: it
// would make "02" read like a two-level WBS id.
func TestNodeIDOrderingIsStable(t *testing.T) {
	got := []string{nodeIDFor(11), nodeIDFor(2), nodeIDFor(10), nodeIDFor(1), nodeIDFor(9)}
	want := []string{"11", "2", "10", "1", "9"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("ids = %v, want %v", got, want)
	}
	for _, v := range got {
		if strings.HasPrefix(v, "0") {
			t.Errorf("id %q is zero-padded; that reads as a WBS level, not a sequence", v)
		}
	}
	// plan.Less is numeric per segment, so 2 sorts before 10 without padding.
	if !plan.Less("2", "10") {
		t.Error("plan.Less(2,10) is false, so unpadded ids would sort wrongly")
	}
	if !plan.Less("1", "2") {
		t.Error("plan.Less(1,2) is false")
	}
}

func mustPlan(t *testing.T, src string) *plan.Plan {
	t.Helper()
	p, err := plan.Parse([]byte(src))
	if err != nil {
		t.Fatal(err)
	}
	return p
}

func ids(p *plan.Plan) []string {
	out := make([]string, 0, len(p.Nodes))
	for _, n := range p.Nodes {
		if n != nil {
			out = append(out, n.ID)
		}
	}
	return out
}
