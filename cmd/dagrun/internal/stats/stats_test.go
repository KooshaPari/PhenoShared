package stats

import (
	"bytes"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
)

// writeRun installs a run directory. An empty state means "no state.json yet",
// which is a real state for a run that has not started.
func writeRun(t *testing.T, planYAML, stateJSON string) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), []byte(planYAML), 0o644); err != nil {
		t.Fatalf("write run.yaml: %v", err)
	}
	if stateJSON != "" {
		if err := os.WriteFile(filepath.Join(dir, "state.json"), []byte(stateJSON), 0o644); err != nil {
			t.Fatalf("write state.json: %v", err)
		}
	}
	return dir
}

func findKind(t *testing.T, r *Report, kind string) Kind {
	t.Helper()
	for _, k := range r.Kinds {
		if k.Kind == kind {
			return k
		}
	}
	t.Fatalf("kind %q not in report", kind)
	return Kind{}
}

func TestComputeCounts(t *testing.T) {
	planYAML := `version: 1
run: counts
nodes:
  - {id: "1", kind: IMPL, title: done-clean, estimate: 10m}
  - {id: "2", kind: IMPL, title: done-retried, estimate: 10m}
  - {id: "3", kind: IMPL, title: failed, estimate: 10m}
  - {id: "4", kind: GATE, title: pending, estimate: 1m}
`
	stateJSON := `{"version":1,"run":"counts","nodes":{
  "1":{"status":"done","attempts":0,"duration_ms":1000},
  "2":{"status":"done","attempts":2,"duration_ms":2000},
  "3":{"status":"failed","attempts":1,"duration_ms":500},
  "4":{"status":"pending"}
}}`
	r, err := Compute(writeRun(t, planYAML, stateJSON))
	if err != nil {
		t.Fatalf("Compute: %v", err)
	}

	cases := []struct {
		kind  string
		nodes int
		done  int
		fail  int
		retry int
		adopt int
	}{
		{"IMPL", 3, 2, 1, 1, 1},
		{"GATE", 1, 0, 0, 0, 0},
	}
	for _, c := range cases {
		got := findKind(t, r, c.kind)
		if got.Nodes != c.nodes || got.Done != c.done || got.Failed != c.fail ||
			got.Retried != c.retry || got.Adopted != c.adopt {
			t.Errorf("%s = %+v, want nodes=%d done=%d failed=%d retried=%d adopted=%d",
				c.kind, got, c.nodes, c.done, c.fail, c.retry, c.adopt)
		}
	}
	if r.Nodes != 4 {
		t.Errorf("Nodes = %d, want 4", r.Nodes)
	}
	if len(r.Kinds) != 2 || r.Kinds[0].Kind != "GATE" || r.Kinds[1].Kind != "IMPL" {
		t.Errorf("kinds not sorted by name: %+v", r.Kinds)
	}
}

func TestComputeMedianEvenAndOdd(t *testing.T) {
	cases := []struct {
		name string
		plan string
		du   []int
		want int64
	}{
		{
			name: "odd three samples takes the middle",
			plan: `version: 1
run: odd
nodes:
  - {id: "1", kind: IMPL, title: a, estimate: 10m}
  - {id: "2", kind: IMPL, title: b, estimate: 10m}
  - {id: "3", kind: IMPL, title: c, estimate: 10m}
`,
			du:   []int{3000, 1000, 2000},
			want: 2000,
		},
		{
			name: "even two samples takes the lower middle",
			plan: `version: 1
run: even
nodes:
  - {id: "1", kind: IMPL, title: a, estimate: 10m}
  - {id: "2", kind: IMPL, title: b, estimate: 10m}
`,
			du:   []int{3000, 1000},
			want: 1000,
		},
		{
			name: "even four samples takes the lower middle",
			plan: `version: 1
run: even4
nodes:
  - {id: "1", kind: IMPL, title: a, estimate: 10m}
  - {id: "2", kind: IMPL, title: b, estimate: 10m}
  - {id: "3", kind: IMPL, title: c, estimate: 10m}
  - {id: "4", kind: IMPL, title: d, estimate: 10m}
`,
			du:   []int{4000, 2000, 3000, 1000},
			want: 2000,
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			rows := make([]string, 0, len(c.du))
			for i, d := range c.du {
				rows = append(rows, fmt.Sprintf(`%q:{"status":"done","duration_ms":%d}`, strconv.Itoa(i+1), d))
			}
			stateJSON := `{"version":1,"nodes":{` + strings.Join(rows, ",") + "}}"
			r, err := Compute(writeRun(t, c.plan, stateJSON))
			if err != nil {
				t.Fatalf("Compute: %v", err)
			}
			if got := findKind(t, r, "IMPL").MedianMS; got != c.want {
				t.Errorf("MedianMS = %d, want %d", got, c.want)
			}
		})
	}
}

func TestComputeKindWithoutDurations(t *testing.T) {
	planYAML := `version: 1
run: nodur
nodes:
  - {id: "1", kind: IMPL, title: a, estimate: 10m}
  - {id: "2", kind: RESEARCH, title: b, estimate: 10m}
  - {id: "3", kind: RESEARCH, title: c, estimate: 10m}
`
	stateJSON := `{"version":1,"nodes":{
  "1":{"status":"done","duration_ms":1500},
  "2":{"status":"done"},
  "3":{"status":"running"}
}}`
	r, err := Compute(writeRun(t, planYAML, stateJSON))
	if err != nil {
		t.Fatalf("Compute: %v", err)
	}
	if got := findKind(t, r, "RESEARCH").MedianMS; got != 0 {
		t.Errorf("MedianMS for unmeasured kind = %d, want 0", got)
	}
	if r.Measured != 1 {
		t.Errorf("Measured = %d, want 1", r.Measured)
	}
	if r.TotalMS != 1500 {
		t.Errorf("TotalMS = %d, want 1500", r.TotalMS)
	}
	// The table must still print "-" for a kind with no samples.
	var buf bytes.Buffer
	if err := Render(&buf, r); err != nil {
		t.Fatalf("Render: %v", err)
	}
	var row string
	for _, line := range strings.Split(buf.String(), "\n") {
		if strings.HasPrefix(line, "RESEARCH") {
			row = line
		}
	}
	if row == "" || !strings.HasSuffix(row, "-") {
		t.Errorf("unmeasured kind row should end with a dash median, got %q in:\n%s", row, buf.String())
	}
}

func TestComputeNoState(t *testing.T) {
	planYAML := `version: 1
run: fresh
nodes:
  - {id: "1", kind: IMPL, title: a, estimate: 10m}
  - {id: "2", kind: GATE, title: b, estimate: 1m}
`
	r, err := Compute(writeRun(t, planYAML, ""))
	if err != nil {
		t.Fatalf("Compute on a run with no state: %v", err)
	}
	if r.Run != "fresh" || r.Nodes != 2 {
		t.Errorf("report = run %q nodes %d, want fresh/2", r.Run, r.Nodes)
	}
	for _, k := range r.Kinds {
		if k.Done != 0 || k.Failed != 0 || k.Retried != 0 || k.Adopted != 0 {
			t.Errorf("%s should be all pending, got %+v", k.Kind, k)
		}
		if k.Nodes != 1 {
			t.Errorf("%s nodes = %d, want 1", k.Kind, k.Nodes)
		}
	}
	if r.Measured != 0 {
		t.Errorf("Measured = %d, want 0", r.Measured)
	}
	if len(r.Durations) != 0 {
		t.Errorf("Durations = %v, want empty", r.Durations)
	}
}

func TestRenderDeterministic(t *testing.T) {
	planYAML := `version: 1
run: stable
max_cost_usd: 5
nodes:
  - {id: "1", kind: IMPL, title: a, estimate: 10m}
  - {id: "2", kind: IMPL, title: b, estimate: 10m}
  - {id: "3", kind: GATE, title: c, estimate: 1m}
  - {id: "4", kind: RESEARCH, title: d, estimate: 4m}
`
	stateJSON := `{"version":1,"nodes":{
  "1":{"status":"done","duration_ms":1000,"usage":{"input_tokens":10,"output_tokens":5}},
  "2":{"status":"failed","duration_ms":2000,"attempts":2},
  "3":{"status":"done","duration_ms":500},
  "4":{"status":"pending"}
}}`
	r, err := Compute(writeRun(t, planYAML, stateJSON))
	if err != nil {
		t.Fatalf("Compute: %v", err)
	}
	var first, second bytes.Buffer
	if err := Render(&first, r); err != nil {
		t.Fatalf("Render first: %v", err)
	}
	if err := Render(&second, r); err != nil {
		t.Fatalf("Render second: %v", err)
	}
	if !bytes.Equal(first.Bytes(), second.Bytes()) {
		t.Fatalf("Render is not deterministic:\n--- first ---\n%s\n--- second ---\n%s", first.String(), second.String())
	}
}
