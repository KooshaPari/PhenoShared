package main

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/KooshaPari/dagrun/internal/trace"
)

// The agent-driven path must leave the same kind of record behind as the
// automated path.
//
// The trace is the DAG's only record, so a node whose state moved without an
// event looks like a node that never ran. That was the defect: `dagrun next`,
// `dagrun claim` and `dagrun done` moved the node through the store and
// wrote nothing, so `dagrun trace` answered "no events yet" for a run an
// agent had already claimed and completed, while `dagrun run` recorded
// run.start, node.adopt and run.end for the same plan.
func TestAgentDrivenPathWritesTraceEvents(t *testing.T) {
	root := t.TempDir()
	t.Chdir(root)

	planBody := `version: 1
run: agent-driven
intent: prove the agent-driven path is traced
max_parallel: 4
nodes:
  - id: "1.1"
    kind: DOC
    title: write the notes
    artifacts:
      - path: artifacts/NOTES.md
        min_bytes: 4
`
	planPath := filepath.Join(root, "plan.yaml")
	if err := os.WriteFile(planPath, []byte(planBody), 0o644); err != nil {
		t.Fatalf("write plan: %v", err)
	}
	runDir := filepath.Join(root, ".dagrun")
	if err := cmdPlan([]string{"--dir", runDir, planPath}); err != nil {
		t.Fatalf("plan: %v", err)
	}

	// The node's contract has to hold for `done` to accept it, so the test
	// walks the real path rather than the --force shortcut.
	if err := os.MkdirAll(filepath.Join(root, "artifacts"), 0o755); err != nil {
		t.Fatalf("mkdir artifacts: %v", err)
	}
	artifact := filepath.Join(root, "artifacts", "NOTES.md")
	if err := os.WriteFile(artifact, []byte("# Notes\n\nThe agent-driven path writes a trace.\n"), 0o644); err != nil {
		t.Fatalf("write artifact: %v", err)
	}

	if err := cmdNext([]string{"--dir", runDir}); err != nil {
		t.Fatalf("next: %v", err)
	}
	if err := cmdClaim([]string{"--dir", runDir, "--owner", "agent-1", "1.1"}); err != nil {
		t.Fatalf("claim: %v", err)
	}
	if err := cmdDone([]string{"--dir", runDir, "1.1"}); err != nil {
		t.Fatalf("done: %v", err)
	}

	traceDir := filepath.Join(runDir, "trace")
	assertTraceNonEmpty(t, traceDir)

	events, err := trace.Merge(traceDir)
	if err != nil {
		t.Fatalf("merge trace: %v", err)
	}
	claim, ok := findEvent(events, "1.1", "node.claim")
	if !ok {
		t.Fatalf("no node.claim event for node 1.1; trace holds %d event(s): %+v", len(events), events)
	}
	if claim.Worker != "agent-1" {
		t.Errorf("node.claim worker = %q, want %q", claim.Worker, "agent-1")
	}
	if claim.Run != "agent-driven" {
		t.Errorf("node.claim run = %q, want %q", claim.Run, "agent-driven")
	}
	if claim.TS.IsZero() {
		t.Error("node.claim carries no timestamp, so the claim has no \"when\"")
	}
	if claim.Epoch == 0 {
		t.Error("node.claim carries no epoch, so it cannot be tied to the claim that won")
	}
	if _, ok := findEvent(events, "1.1", "node.done"); !ok {
		t.Fatalf("no node.done event for node 1.1; trace holds %d event(s): %+v", len(events), events)
	}
}

// assertTraceNonEmpty fails when the trace directory is missing or holds no
// bytes, which is exactly the shape of the defect: the directory is created
// by the store, and it stays empty when nothing writes an event.
func assertTraceNonEmpty(t *testing.T, dir string) {
	t.Helper()
	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("trace directory %s: %v", dir, err)
	}
	shards := 0
	for _, e := range entries {
		if e.IsDir() || filepath.Ext(e.Name()) != ".jsonl" {
			continue
		}
		shards++
		info, err := e.Info()
		if err != nil {
			t.Fatalf("stat %s: %v", e.Name(), err)
		}
		if info.Size() == 0 {
			t.Errorf("trace shard %s is empty", e.Name())
		}
	}
	if shards == 0 {
		t.Fatalf("no trace shard written to %s", dir)
	}
}

// findEvent returns the first event for a node with the given name.
func findEvent(events []trace.Event, node, name string) (trace.Event, bool) {
	for _, e := range events {
		if e.Node == node && e.Event == name {
			return e, true
		}
	}
	return trace.Event{}, false
}
