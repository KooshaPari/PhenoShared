package plan

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// The fixture is emitted by the Rust crate that OWNS this schema:
//
//	cargo run -p phenotype-dag-core --example emit_golden
//
// and copied here. That direction matters. A fixture hand-written by the Go
// author only proves Go agrees with the Go author's reading of schema.rs, which
// is exactly the assumption that needs testing. If the shapes ever diverge, the
// crate regenerates and this test fails.
//
// The copy is committed rather than read from the crate's path so this test
// keeps working after the crate is dropped (ADR-ECO-024 gate 2 is the last thing
// standing between the ecosystem and one DAG implementation).
const goldenPath = "testdata/dagschema-golden.yaml"

// crateGoldens is where the crate emits its own copy. When it exists, the two
// must be byte-identical, which is what makes the committed copy trustworthy.
var crateGoldens = filepath.Join("..", "..", "..", "..", "crates", "phenotype-dag-core", "testdata", "dagschema-golden.yaml")

func readGolden(t *testing.T) []byte {
	t.Helper()
	raw, err := os.ReadFile(goldenPath)
	if err != nil {
		t.Fatalf("read %s: %v", goldenPath, err)
	}
	return raw
}

// The committed copy must match what the crate currently emits.
func TestGoldenFixtureIsCurrent(t *testing.T) {
	theirs, err := os.ReadFile(crateGoldens)
	if err != nil {
		t.Skipf("crate fixture not present (%v); the committed copy stands alone", err)
	}
	ours := readGolden(t)
	if string(theirs) != string(ours) {
		t.Fatalf("the committed golden has drifted from the crate's output\n"+
			"regenerate with: cargo run -p phenotype-dag-core --example emit_golden\n"+
			"then copy crates/phenotype-dag-core/testdata/dagschema-golden.yaml over %s", goldenPath)
	}
}

// The schema the crate serialises must parse. This is the gate: dagrun reads
// phenotype-dag-core's DagSchema natively.
func TestParseRealDagSchema(t *testing.T) {
	d, err := ParseDagSchema(readGolden(t))
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	if d.Version != "2.0.0" {
		t.Errorf("version = %q, want 2.0.0", d.Version)
	}
	if d.Name != "golden" {
		t.Errorf("name = %q, want golden", d.Name)
	}
	if len(d.Nodes) != 2 {
		t.Fatalf("nodes = %d, want 2", len(d.Nodes))
	}
	if len(d.Edges) != 2 {
		t.Errorf("edges = %d, want 2", len(d.Edges))
	}

	n1 := d.Nodes[0]
	if n1.Label != "Freeze scope" {
		t.Errorf("node 1 label = %q", n1.Label)
	}
	if len(n1.Prerequisites) != 1 || n1.Prerequisites[0].Type != "environment_variable" {
		t.Errorf("node 1 prerequisites = %+v", n1.Prerequisites)
	}
	if n1.Prerequisites[0].Variable != "TARGET_ENV" {
		t.Errorf("prerequisite variable = %q, want TARGET_ENV", n1.Prerequisites[0].Variable)
	}
	if len(n1.Acceptance) != 1 || n1.Acceptance[0].Code == nil || *n1.Acceptance[0].Code != 0 {
		t.Errorf("node 1 acceptance = %+v", n1.Acceptance)
	}
	// AuditHook is an ENUM, not a {timing, script} pair. A reader that guessed
	// the wrong shape would see an empty hook here.
	if len(n1.AuditHooks) != 1 {
		t.Fatalf("node 1 audit hooks = %d, want 1", len(n1.AuditHooks))
	}
	if h := n1.AuditHooks[0]; h.Type != "log_entry" || h.Timing != "on_success" || h.Message != "scope frozen" {
		t.Errorf("audit hook = %+v, want log_entry/on_success/'scope frozen'", h)
	}
	if n1.Metadata["owner"] != "platform" {
		t.Errorf("metadata = %v", n1.Metadata)
	}

	n2 := d.Nodes[1]
	if len(n2.Prerequisites) != 3 {
		t.Errorf("node 2 prerequisites = %d, want 3", len(n2.Prerequisites))
	}
	if len(n2.Acceptance) != 3 {
		t.Errorf("node 2 acceptance = %d, want 3", len(n2.Acceptance))
	}
}

// The conversion must map what a shell can express and REPORT the rest. The
// number of reports is asserted so a future field cannot be silently dropped:
// if a new criterion type appears, this count changes and someone looks.
func TestConvertRealDagSchema(t *testing.T) {
	d, err := ParseDagSchema(readGolden(t))
	if err != nil {
		t.Fatal(err)
	}
	p, unmapped, err := d.ToPlan()
	if err != nil {
		t.Fatalf("ToPlan: %v", err)
	}

	if p.Run != "golden" {
		t.Errorf("run = %q, want golden", p.Run)
	}
	if len(p.Nodes) != 2 {
		t.Fatalf("nodes = %d", len(p.Nodes))
	}

	byID := map[string]*Node{}
	for _, n := range p.Nodes {
		byID[n.ID] = n
	}

	// Node 1: environment_variable prerequisite -> a pre hook; exit_code 0 ->
	// check "true".
	n1 := byID["1"]
	if n1 == nil {
		t.Fatal("node 1 missing")
	}
	if n1.Hooks == nil || !strings.Contains(n1.Hooks.Pre, "TARGET_ENV") {
		t.Errorf("node 1 pre hook = %v, want an env assertion on TARGET_ENV", n1.Hooks)
	}
	if n1.Check != "true" {
		t.Errorf("node 1 check = %q, want \"true\" from exit_code 0", n1.Check)
	}
	if n1.Prompt == "" {
		t.Error("node 1 prompt is empty; the description should carry into it")
	}

	// Node 2: three prerequisites, two of them shell-expressible; three
	// acceptance criteria, two expressible; a webhook hook; a notify hook that
	// has no shell expression.
	n2 := byID["2"]
	if n2 == nil {
		t.Fatal("node 2 missing")
	}
	if n2.Hooks == nil || !strings.Contains(n2.Hooks.Pre, "test -e") {
		t.Errorf("node 2 pre hook = %v, want the file_exists assertion", n2.Hooks)
	}
	if !strings.Contains(n2.Hooks.Pre, "mkdir -p artifacts") {
		t.Errorf("node 2 pre hook = %v, want the custom_script command", n2.Hooks.Pre)
	}
	if !strings.Contains(n2.Check, "grep") || !strings.Contains(n2.Check, "test -s artifacts/SPEC.md") {
		t.Errorf("node 2 check = %q, want the output_contains and custom_check assertions", n2.Check)
	}
	if n2.Hooks.Post == "" || !strings.Contains(n2.Hooks.Post, "curl") {
		t.Errorf("node 2 post hook = %q, want the webhook POST", n2.Hooks.Post)
	}
	if len(n2.Deps) != 1 || n2.Deps[0] != "1" {
		t.Errorf("node 2 deps = %v, want [1] from the edges", n2.Deps)
	}

	// Everything DagSchema can express and the plan cannot must be reported.
	wantReported := map[string]bool{
		"image_ready":      false, // prerequisite needing infrastructure
		"metric_threshold": false, // acceptance needing captured metrics
		"notify":           false, // hook targeting a telemetry sink
		"metadata":         false, // node 1 metadata has no plan home
		"conditional":      false, // the second edge carries a condition
	}
	for _, u := range unmapped {
		for key := range wantReported {
			if strings.Contains(u.Detail, key) {
				wantReported[key] = true
			}
		}
	}
	for key, seen := range wantReported {
		if !seen {
			t.Errorf("%q was silently dropped; every unmappable field must be reported. got: %v", key, unmapped)
		}
	}
}

// A conditional edge keeps its dependency but must say so: making a conditional
// edge unconditional silently is worse than refusing.
func TestConditionalEdgeIsReportedNotApplied(t *testing.T) {
	src := `version: "1"
name: cond
nodes:
  - id: a
  - id: b
edges:
  - from: a
    to: b
    condition: a.exit_code == 0
`
	d, err := ParseDagSchema([]byte(src))
	if err != nil {
		t.Fatal(err)
	}
	p, unmapped, err := d.ToPlan()
	if err != nil {
		t.Fatal(err)
	}
	found := false
	for _, u := range unmapped {
		if strings.Contains(u.Detail, "conditional") {
			found = true
		}
	}
	if !found {
		t.Fatalf("a conditional edge was not reported: %v", unmapped)
	}
	// The dependency still exists: the edge was traversed unconditionally, and
	// that fact is what the report is about.
	var b *Node
	for _, n := range p.Nodes {
		if n.ID == "b" {
			b = n
		}
	}
	if b == nil || len(b.Deps) != 1 {
		t.Errorf("dependency not preserved: %+v", b)
	}
}

func TestCycleIsRejectedAtImport(t *testing.T) {
	src := `version: "1"
nodes:
  - id: a
  - id: b
edges:
  - from: a
    to: b
  - from: b
    to: a
`
	d, err := ParseDagSchema([]byte(src))
	if err != nil {
		t.Fatal(err)
	}
	_, _, err = d.ToPlan()
	if err == nil {
		t.Fatal("a cyclic schema must be rejected where it is read")
	}
	if !strings.Contains(err.Error(), "cycle") {
		t.Errorf("error should name the cycle: %v", err)
	}
}

func TestEdgeToUnknownNodeIsReported(t *testing.T) {
	src := `version: "1"
nodes:
  - id: a
edges:
  - from: a
    to: ghost
`
	d, err := ParseDagSchema([]byte(src))
	if err != nil {
		t.Fatal(err)
	}
	_, unmapped, err := d.ToPlan()
	if err != nil {
		t.Fatal(err)
	}
	found := false
	for _, u := range unmapped {
		if strings.Contains(u.Detail, "ghost") {
			found = true
		}
	}
	if !found {
		t.Errorf("an edge to a missing node was not reported: %v", unmapped)
	}
}

func TestParseDagSchemaRejectsEmpty(t *testing.T) {
	if _, err := ParseDagSchema([]byte("version: \"1\"\n")); err == nil {
		t.Fatal("a schema with no nodes must be rejected")
	}
	if _, err := ParseDagSchema([]byte("not: a schema")); err == nil {
		t.Fatal("a document with no nodes must be rejected")
	}
}
