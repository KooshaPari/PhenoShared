// Package otel exports a run as OpenTelemetry spans.
//
// This is an EXPORTER, not a client. dagrun never opens a connection to a
// collector, for the same reason state lives in a JSON file: a tool that every
// agent process depends on must not fail because a sidecar is down. The document
// is emitted; a collector comes and gets it.
//
// The hand-rolled encoding is deliberate. Pulling in opentelemetry-go would add
// a dependency tree to a single-binary tool for one output format, and the OTLP
// JSON shape is small enough to write honestly. Nothing here changes the trace:
// the DAG stays the source of truth, and these spans are a projection of it.
package otel

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/trace"
)

// Status codes, per the OTLP JSON schema.
const (
	StatusUnset = 0
	StatusOK    = 1
	StatusError = 2
)

// Span kinds, per the OTLP JSON schema.
const (
	SpanKindInternal = 1
	SpanKindServer   = 2
	SpanKindClient   = 3
)

// Attribute is one span attribute.
type Attribute struct {
	Key   string `json:"key"`
	Value Value  `json:"value"`
}

// Value is an AnyValue. Exactly one field is set.
type Value struct {
	StringValue *string  `json:"stringValue,omitempty"`
	IntValue    *string  `json:"intValue,omitempty"`
	BoolValue   *bool    `json:"boolValue,omitempty"`
	DoubleValue *float64 `json:"doubleValue,omitempty"`
}

// Status is a span status.
type Status struct {
	Code    int    `json:"code,omitempty"`
	Message string `json:"message,omitempty"`
}

// Span is one OTLP span. IDs are hex strings of 32 and 16 characters.
type Span struct {
	TraceID       string      `json:"traceId"`
	SpanID        string      `json:"spanId"`
	ParentID      string      `json:"parentSpanId,omitempty"`
	Name          string      `json:"name"`
	Kind          int         `json:"kind"`
	StartUnixNano uint64      `json:"startTimeUnixNano,string"`
	EndUnixNano   uint64      `json:"endTimeUnixNano,string"`
	Status        Status      `json:"status"`
	Attributes    []Attribute `json:"attributes,omitempty"`
}

// RunDir is the resolved run directory plus its plan and merged trace.
type RunDir struct {
	Dir    string
	Plan   *plan.Plan
	Events []trace.Event
}

// Open reads a run directory. The plan is required; a missing trace is not an
// error, because a planned-but-never-run directory is a legitimate state and an
// exporter that refuses it is less useful than one that emits the root span.
func Open(dir string) (*RunDir, error) {
	raw, err := os.ReadFile(filepath.Join(dir, "run.yaml"))
	if err != nil {
		return nil, fmt.Errorf("read plan in %s: %w", dir, err)
	}
	p, err := plan.Parse(raw)
	if err != nil {
		return nil, fmt.Errorf("parse plan in %s: %w", dir, err)
	}
	events, err := trace.Merge(filepath.Join(dir, "trace"))
	if err != nil {
		return nil, err
	}
	return &RunDir{Dir: dir, Plan: p, Events: events}, nil
}

// Build derives spans for a run directory.
func Build(dir string) ([]Span, error) {
	rd, err := Open(dir)
	if err != nil {
		return nil, err
	}
	return SpansOf(rd), nil
}

// SpansOf derives spans from an already-opened run.
//
// Hierarchy: one root span for the run, and one span per executed node whose
// parent is the root UNLESS a dependency genuinely finished before this node
// started. That rule is the honest one. Two nodes that ran concurrently are not
// parent and child, and inventing a causal chain from the dependency graph would
// make a waterfall that lies about which work was serial.
func SpansOf(rd *RunDir) []Span {
	runID := rd.Plan.Run
	traceID := deriveID(runID, "run", 16)

	// Per-node timing from the trace. node.claim starts, node.done/node.exit end.
	type timing struct {
		start, end time.Time
		status     string
		attempts   int
	}
	times := map[string]*timing{}
	for _, e := range rd.Events {
		if e.Node == "" {
			continue
		}
		t := times[e.Node]
		if t == nil {
			t = &timing{}
			times[e.Node] = t
		}
		switch e.Event {
		case "node.claim":
			if t.start.IsZero() || e.TS.Before(t.start) {
				t.start = e.TS
			}
			if e.Attempt > t.attempts {
				t.attempts = e.Attempt
			}
		case "node.done":
			t.status = "done"
			if !e.TS.Before(t.end) {
				t.end = e.TS
			}
		case "node.exit":
			if t.status == "" {
				t.status = "exited"
			}
			if !e.TS.Before(t.end) {
				t.end = e.TS
			}
		case "node.fail", "hook.pre.failed", "hook.post.failed":
			t.status = "failed"
			if !e.TS.Before(t.end) {
				t.end = e.TS
			}
		}
	}

	// Run window: first and last event of any kind.
	var runStart, runEnd time.Time
	for _, e := range rd.Events {
		if runStart.IsZero() || e.TS.Before(runStart) {
			runStart = e.TS
		}
		if e.TS.After(runEnd) {
			runEnd = e.TS
		}
	}

	root := Span{
		TraceID: traceID,
		SpanID:  deriveID(runID, "run", 8),
		Name:    "dagrun.run",
		Kind:    SpanKindServer,
		Status:  Status{Code: StatusUnset},
		Attributes: []Attribute{
			strAttr("dagrun.run", runID),
			intAttr("dagrun.nodes", len(rd.Plan.Nodes)),
		},
	}
	if !runStart.IsZero() {
		root.StartUnixNano = nano(runStart)
		root.EndUnixNano = nano(runEnd)
	}

	nodes := make([]*plan.Node, 0, len(rd.Plan.Nodes))
	for _, n := range rd.Plan.Nodes {
		if n != nil {
			nodes = append(nodes, n)
		}
	}
	sort.Slice(nodes, func(i, j int) bool { return plan.Less(nodes[i].ID, nodes[j].ID) })

	spans := make([]Span, 0, len(nodes)+1)
	spans = append(spans, root)

	spanIDOf := map[string]string{}
	for _, n := range nodes {
		spanIDOf[n.ID] = deriveID(runID, n.ID, 8)
	}

	for _, n := range nodes {
		t := times[n.ID]
		sp := Span{
			TraceID:  traceID,
			SpanID:   spanIDOf[n.ID],
			ParentID: root.SpanID,
			Name:     "dagrun.node." + n.ID,
			Kind:     SpanKindInternal,
		}
		status := "not_run"
		if t != nil {
			if !t.start.IsZero() {
				sp.StartUnixNano = nano(t.start)
			}
			if !t.end.IsZero() {
				sp.EndUnixNano = nano(t.end)
			}
			if t.status != "" {
				status = t.status
			}
		}
		switch status {
		case "done":
			sp.Status = Status{Code: StatusOK}
		case "failed":
			sp.Status = Status{Code: StatusError, Message: "node failed"}
		}
		if status == "not_run" {
			sp.Status = Status{Code: StatusUnset, Message: "no execution recorded for this node"}
		}

		// The honest parent rule: a dependency becomes the parent only when it
		// actually finished before this node started.
		for _, dep := range n.Deps {
			dt, dok := times[dep]
			if !dok || dt.end.IsZero() || t == nil || t.start.IsZero() {
				continue
			}
			if dt.end.Before(t.start) || dt.end.Equal(t.start) {
				sp.ParentID = spanIDOf[dep]
				break
			}
		}

		attempts := 0
		if t != nil {
			attempts = t.attempts
		}
		sp.Attributes = []Attribute{
			strAttr("dagrun.node.id", n.ID),
			strAttr("dagrun.node.kind", n.Kind),
			strAttr("dagrun.node.role", n.Role),
			strAttr("dagrun.node.status", status),
			intAttr("dagrun.node.attempts", attempts),
			intAttr("dagrun.node.artifacts", len(n.Artifacts)),
			strAttr("dagrun.node.deps", joinDeps(n.Deps)),
		}
		spans = append(spans, sp)
	}
	return spans
}

// SpanFor is a convenience for callers that want one node's span.
func SpanFor(dir, nodeID string) (Span, bool) {
	spans, err := Build(dir)
	if err != nil {
		return Span{}, false
	}
	for _, s := range spans {
		if s.Name == "dagrun.node."+nodeID {
			return s, true
		}
	}
	return Span{}, false
}

// Write emits the OTLP/JSON envelope.
func Write(w io.Writer, spans []Span) error {
	doc := map[string]any{
		"resourceSpans": []any{
			map[string]any{
				"resource": map[string]any{
					"attributes": []Attribute{
						strAttr("service.name", "dagrun"),
					},
				},
				"scopeSpans": []any{
					map[string]any{
						"scope": map[string]any{"name": "dagrun", "version": versionOf(spans)},
						"spans": spans,
					},
				},
			},
		},
	}
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	return enc.Encode(doc)
}

// versionOf is a placeholder scope version: the exporter has no build version of
// its own, and inventing one would make the span look more authoritative than it
// is. The run id is already on the root span.
func versionOf([]Span) string { return "1" }

// deriveID produces a deterministic hex id of n bytes from the run and node, so
// re-exporting the same run yields identical trace and span ids. A random id
// would make two exports of one run look like two runs.
func deriveID(run, node string, n int) string {
	sum := sha256.Sum256([]byte("dagrun\x00" + run + "\x00" + node))
	return hex.EncodeToString(sum[:n])
}

func nano(t time.Time) uint64 {
	if t.IsZero() {
		return 0
	}
	return uint64(t.UnixNano())
}

func joinDeps(deps []string) string {
	if len(deps) == 0 {
		return ""
	}
	out := deps[0]
	for _, d := range deps[1:] {
		out += "," + d
	}
	return out
}

func strAttr(k, v string) Attribute {
	s := v
	return Attribute{Key: k, Value: Value{StringValue: &s}}
}

func intAttr(k string, v int) Attribute {
	s := fmt.Sprintf("%d", v)
	return Attribute{Key: k, Value: Value{IntValue: &s}}
}
