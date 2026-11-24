package otel

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/trace"
)

const testPlan = `version: 1
run: otel-probe
nodes:
  - id: "1"
    kind: INTENT
    title: first
    artifacts:
      - path: artifacts/one.md
        min_bytes: 1
  - id: "2"
    kind: IMPL
    title: second, depends on one
    deps: ["1"]
    artifacts:
      - path: artifacts/two.md
        min_bytes: 1
  - id: "3"
    kind: IMPL
    title: concurrent sibling
    artifacts:
      - path: artifacts/three.md
        min_bytes: 1
`

func writeRun(t *testing.T, dir string, events []trace.Event) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), []byte(testPlan), 0o644); err != nil {
		t.Fatal(err)
	}
	trDir := filepath.Join(dir, "trace")
	if err := os.MkdirAll(trDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if len(events) == 0 {
		return
	}
	w := trace.New(trDir)
	for _, e := range events {
		if err := w.Emit("test-worker", e); err != nil {
			t.Fatal(err)
		}
	}
}

func TestBuildProducesOneSpanPerNodePlusARoot(t *testing.T) {
	dir := t.TempDir()
	base := time.Date(2026, 11, 10, 3, 0, 0, 0, time.UTC)
	writeRun(t, dir, []trace.Event{
		{TS: base, Run: "otel-probe", Event: "run.start"},
		{TS: base.Add(1 * time.Second), Node: "1", Event: "node.claim"},
		{TS: base.Add(2 * time.Second), Node: "1", Event: "node.done"},
		{TS: base.Add(3 * time.Second), Node: "2", Event: "node.claim"},
		{TS: base.Add(4 * time.Second), Node: "2", Event: "node.done"},
		{TS: base.Add(5 * time.Second), Node: "3", Event: "node.claim"},
		{TS: base.Add(6 * time.Second), Node: "3", Event: "node.fail"},
	})

	spans, err := Build(dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(spans) != 4 {
		t.Fatalf("got %d spans, want 4 (root + 3 nodes)", len(spans))
	}
	if spans[0].Name != "dagrun.run" {
		t.Errorf("first span = %q, want the run root", spans[0].Name)
	}
	seen := map[string]bool{}
	for _, s := range spans[1:] {
		seen[s.Name] = true
	}
	for _, want := range []string{"dagrun.node.1", "dagrun.node.2", "dagrun.node.3"} {
		if !seen[want] {
			t.Errorf("missing span %q", want)
		}
	}
}

func TestBuildIDsAreDeterministic(t *testing.T) {
	dir := t.TempDir()
	base := time.Date(2026, 11, 10, 3, 0, 0, 0, time.UTC)
	writeRun(t, dir, []trace.Event{
		{TS: base, Event: "run.start"},
		{TS: base.Add(time.Second), Node: "1", Event: "node.claim"},
		{TS: base.Add(2 * time.Second), Node: "1", Event: "node.done"},
	})

	first, err := Build(dir)
	if err != nil {
		t.Fatal(err)
	}
	second, err := Build(dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(first) != len(second) {
		t.Fatalf("span count changed between exports")
	}
	for i := range first {
		if first[i].TraceID != second[i].TraceID || first[i].SpanID != second[i].SpanID {
			t.Fatalf("span %d ids changed between exports: %s/%s vs %s/%s",
				i, first[i].TraceID, first[i].SpanID, second[i].TraceID, second[i].SpanID)
		}
	}
	if len(first[0].TraceID) != 32 {
		t.Errorf("traceId = %q, want 32 hex characters", first[0].TraceID)
	}
	if len(first[0].SpanID) != 16 {
		t.Errorf("spanId = %q, want 16 hex characters", first[0].SpanID)
	}
}

// The honest-parent rule: a dependency becomes the parent ONLY when it finished
// before the node started. A concurrent sibling must not be given a fake
// parent, because a waterfall built from that would claim serialisation that
// never happened.
func TestParentIsADependencyOnlyWhenItFinishedFirst(t *testing.T) {
	dir := t.TempDir()
	base := time.Date(2026, 11, 10, 3, 0, 0, 0, time.UTC)
	writeRun(t, dir, []trace.Event{
		{TS: base, Event: "run.start"},
		// Node 1 finishes at +2s; node 2 depends on it and starts at +3s.
		{TS: base.Add(1 * time.Second), Node: "1", Event: "node.claim"},
		{TS: base.Add(2 * time.Second), Node: "1", Event: "node.done"},
		{TS: base.Add(3 * time.Second), Node: "2", Event: "node.claim"},
		{TS: base.Add(4 * time.Second), Node: "2", Event: "node.done"},
		// Node 3 has no deps and runs concurrently with node 2.
		{TS: base.Add(3 * time.Second), Node: "3", Event: "node.claim"},
		{TS: base.Add(5 * time.Second), Node: "3", Event: "node.done"},
	})

	spans, err := Build(dir)
	if err != nil {
		t.Fatal(err)
	}
	byName := map[string]Span{}
	for _, s := range spans {
		byName[s.Name] = s
	}
	root := byName["dagrun.run"]

	if got := byName["dagrun.node.2"].ParentID; got != byName["dagrun.node.1"].SpanID {
		t.Errorf("node 2 parent = %q, want node 1's span %q", got, byName["dagrun.node.1"].SpanID)
	}
	if got := byName["dagrun.node.3"].ParentID; got != root.SpanID {
		t.Errorf("node 3 parent = %q, want the root %q (it ran concurrently, not causally)", got, root.SpanID)
	}
}

func TestSpanStatusReflectsTheOutcome(t *testing.T) {
	dir := t.TempDir()
	base := time.Date(2026, 11, 10, 3, 0, 0, 0, time.UTC)
	writeRun(t, dir, []trace.Event{
		{TS: base, Event: "run.start"},
		{TS: base.Add(time.Second), Node: "1", Event: "node.claim"},
		{TS: base.Add(2 * time.Second), Node: "1", Event: "node.done"},
		{TS: base.Add(3 * time.Second), Node: "2", Event: "node.claim"},
		{TS: base.Add(4 * time.Second), Node: "2", Event: "node.fail"},
	})

	spans, err := Build(dir)
	if err != nil {
		t.Fatal(err)
	}
	byName := map[string]Span{}
	for _, s := range spans {
		byName[s.Name] = s
	}
	if got := byName["dagrun.node.1"].Status.Code; got != StatusOK {
		t.Errorf("a done node has status %d, want %d", got, StatusOK)
	}
	if got := byName["dagrun.node.2"].Status.Code; got != StatusError {
		t.Errorf("a failed node has status %d, want %d", got, StatusError)
	}
	// Node 3 never ran. It must say so rather than claim success.
	n3 := byName["dagrun.node.3"]
	if n3.Status.Code != StatusUnset || n3.Status.Message == "" {
		t.Errorf("an unrun node must be unset with a reason, got %+v", n3.Status)
	}
	if n3.StartUnixNano != 0 || n3.EndUnixNano != 0 {
		t.Errorf("an unrun node must not invent times, got %d..%d", n3.StartUnixNano, n3.EndUnixNano)
	}
}

func TestSpanTimesAreOrdered(t *testing.T) {
	dir := t.TempDir()
	base := time.Date(2026, 11, 10, 3, 0, 0, 0, time.UTC)
	writeRun(t, dir, []trace.Event{
		{TS: base, Event: "run.start"},
		{TS: base.Add(time.Second), Node: "1", Event: "node.claim"},
		{TS: base.Add(2 * time.Second), Node: "1", Event: "node.done"},
	})
	spans, err := Build(dir)
	if err != nil {
		t.Fatal(err)
	}
	for _, s := range spans {
		if s.StartUnixNano == 0 && s.EndUnixNano == 0 {
			continue
		}
		if s.EndUnixNano < s.StartUnixNano {
			t.Errorf("%s ends before it starts: %d..%d", s.Name, s.StartUnixNano, s.EndUnixNano)
		}
	}
}

func TestSpanCarriesTheNodeAttributes(t *testing.T) {
	dir := t.TempDir()
	base := time.Date(2026, 11, 10, 3, 0, 0, 0, time.UTC)
	writeRun(t, dir, []trace.Event{
		{TS: base, Event: "run.start"},
		{TS: base.Add(time.Second), Node: "1", Event: "node.claim", Attempt: 2},
		{TS: base.Add(2 * time.Second), Node: "1", Event: "node.done"},
	})
	spans, err := Build(dir)
	if err != nil {
		t.Fatal(err)
	}
	var node Span
	for _, s := range spans {
		if s.Name == "dagrun.node.1" {
			node = s
		}
	}
	attrs := map[string]string{}
	for _, a := range node.Attributes {
		switch {
		case a.Value.StringValue != nil:
			attrs[a.Key] = *a.Value.StringValue
		case a.Value.IntValue != nil:
			attrs[a.Key] = *a.Value.IntValue
		}
	}
	for key, want := range map[string]string{
		"dagrun.node.id":        "1",
		"dagrun.node.kind":      "INTENT",
		"dagrun.node.status":    "done",
		"dagrun.node.attempts":  "2",
		"dagrun.node.artifacts": "1",
	} {
		if got := attrs[key]; got != want {
			t.Errorf("attribute %s = %q, want %q", key, got, want)
		}
	}
}

// Write must emit a document a collector can parse: valid JSON with the OTLP
// envelope, and int64 fields as strings per the proto3 JSON mapping.
func TestWriteEmitsAParseableOTLPDocument(t *testing.T) {
	dir := t.TempDir()
	base := time.Date(2026, 11, 10, 3, 0, 0, 0, time.UTC)
	writeRun(t, dir, []trace.Event{
		{TS: base, Event: "run.start"},
		{TS: base.Add(time.Second), Node: "1", Event: "node.claim"},
		{TS: base.Add(2 * time.Second), Node: "1", Event: "node.done"},
	})
	spans, err := Build(dir)
	if err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	if err := Write(&buf, spans); err != nil {
		t.Fatal(err)
	}

	var doc map[string]any
	if err := json.Unmarshal(buf.Bytes(), &doc); err != nil {
		t.Fatalf("output is not valid JSON: %v\n%s", err, buf.String())
	}
	rs, ok := doc["resourceSpans"].([]any)
	if !ok || len(rs) != 1 {
		t.Fatalf("resourceSpans = %v, want one entry", doc["resourceSpans"])
	}
	entry := rs[0].(map[string]any)
	scope, ok := entry["scopeSpans"].([]any)
	if !ok || len(scope) != 1 {
		t.Fatalf("scopeSpans missing")
	}
	emitted := scope[0].(map[string]any)["spans"].([]any)
	if len(emitted) != len(spans) {
		t.Errorf("emitted %d spans, want %d", len(emitted), len(spans))
	}
	first := emitted[0].(map[string]any)
	if _, ok := first["startTimeUnixNano"].(string); !ok {
		t.Errorf("startTimeUnixNano must be a string per proto3 JSON, got %T", first["startTimeUnixNano"])
	}
}

func TestBuildOnAPlanThatNeverRanStillEmitsTheRoot(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, nil)
	spans, err := Build(dir)
	if err != nil {
		t.Fatal(err)
	}
	if len(spans) != 4 {
		t.Fatalf("got %d spans, want root plus every declared node", len(spans))
	}
	if spans[0].Name != "dagrun.run" {
		t.Errorf("first span = %q, want the root", spans[0].Name)
	}
	if spans[0].StartUnixNano != 0 || spans[0].EndUnixNano != 0 {
		t.Error("a run with no events must not claim a duration")
	}
}

func TestBuildRejectsAMissingPlan(t *testing.T) {
	if _, err := Build(t.TempDir()); err == nil {
		t.Fatal("expected an error for a directory with no run.yaml")
	}
}

func TestSpanFor(t *testing.T) {
	dir := t.TempDir()
	base := time.Date(2026, 11, 10, 3, 0, 0, 0, time.UTC)
	writeRun(t, dir, []trace.Event{
		{TS: base, Event: "run.start"},
		{TS: base.Add(time.Second), Node: "2", Event: "node.claim"},
		{TS: base.Add(2 * time.Second), Node: "2", Event: "node.done"},
	})
	sp, ok := SpanFor(dir, "2")
	if !ok {
		t.Fatal("SpanFor did not find node 2")
	}
	if !strings.HasSuffix(sp.Name, ".2") {
		t.Errorf("SpanFor returned %q", sp.Name)
	}
	if _, ok := SpanFor(dir, "does-not-exist"); ok {
		t.Error("SpanFor invented a span for an unknown node")
	}
}

// The exporter must not depend on the plan package for anything but reading a
// node; this assertion keeps a future refactor from quietly growing the
// dependency surface.
var _ = plan.Less
