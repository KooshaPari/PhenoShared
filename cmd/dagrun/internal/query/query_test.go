package query

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

const testPlan = `version: 1
run: q
nodes:
  - id: "1"
    kind: INTENT
    role: intent
    title: freeze scope
    artifacts:
      - path: artifacts/INTENT.md
        min_bytes: 1
  - id: "2"
    kind: IMPL
    role: impl
    title: write the thing
    deps: ["1"]
    artifacts:
      - path: src/a.go
        min_bytes: 1
  - id: "3"
    kind: TEST
    role: impl
    title: prove the thing
    deps: ["1"]
    artifacts:
      - path: src/a_test.go
        min_bytes: 1
`

func writeRun(t *testing.T, dir string, state string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), []byte(testPlan), 0o644); err != nil {
		t.Fatal(err)
	}
	if state == "" {
		return
	}
	if err := os.WriteFile(filepath.Join(dir, "state.json"), []byte(state), 0o644); err != nil {
		t.Fatal(err)
	}
}

const testState = `{
  "version": 1,
  "run": "q",
  "nodes": {
    "1": {"status": "done", "attempts": 1},
    "2": {"status": "failed", "attempts": 3, "last_error": "boom"},
    "3": {"status": "running", "attempts": 2, "owner": "host.42.99"}
  }
}`

func mustParse(t *testing.T, args ...string) *Query {
	t.Helper()
	q, err := Parse(args)
	if err != nil {
		t.Fatalf("Parse(%v): %v", args, err)
	}
	return q
}

func TestParseGrammar(t *testing.T) {
	tests := []struct {
		name      string
		args      []string
		wantWhere []Predicate
		wantSel   []string
		wantOrder string
		wantDesc  bool
		wantLimit int
	}{
		{
			name:      "no flags uses the default projection",
			args:      nil,
			wantSel:   DefaultSelect,
			wantLimit: 0,
		},
		{
			name:      "a single where",
			args:      []string{"--where", "status=failed"},
			wantWhere: []Predicate{{Key: "status", Op: "=", Value: "failed"}},
			wantSel:   DefaultSelect,
		},
		{
			name:      "where with an inline equals",
			args:      []string{"--where=kind=IMPL"},
			wantWhere: []Predicate{{Key: "kind", Op: "=", Value: "IMPL"}},
			wantSel:   DefaultSelect,
		},
		{
			name:      "a numeric comparison",
			args:      []string{"--where", "attempt>=2"},
			wantWhere: []Predicate{{Key: "attempt", Op: ">=", Value: "2"}},
			wantSel:   DefaultSelect,
		},
		{
			name:      "select replaces the default",
			args:      []string{"--select", "id,status"},
			wantSel:   []string{"id", "status"},
			wantLimit: 0,
		},
		{
			name:      "order by with a direction",
			args:      []string{"--order-by", "attempts,desc"},
			wantSel:   DefaultSelect,
			wantOrder: "attempts",
			wantDesc:  true,
		},
		{
			name:      "limit",
			args:      []string{"--limit", "5"},
			wantSel:   DefaultSelect,
			wantLimit: 5,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			q := mustParse(t, tc.args...)
			if len(q.Where) != len(tc.wantWhere) {
				t.Fatalf("Where = %v, want %v", q.Where, tc.wantWhere)
			}
			for i := range tc.wantWhere {
				if q.Where[i] != tc.wantWhere[i] {
					t.Errorf("Where[%d] = %v, want %v", i, q.Where[i], tc.wantWhere[i])
				}
			}
			if strings.Join(q.Select, ",") != strings.Join(tc.wantSel, ",") {
				t.Errorf("Select = %v, want %v", q.Select, tc.wantSel)
			}
			if q.OrderBy != tc.wantOrder {
				t.Errorf("OrderBy = %q, want %q", q.OrderBy, tc.wantOrder)
			}
			if q.Desc != tc.wantDesc {
				t.Errorf("Desc = %v, want %v", q.Desc, tc.wantDesc)
			}
			if q.Limit != tc.wantLimit {
				t.Errorf("Limit = %d, want %d", q.Limit, tc.wantLimit)
			}
		})
	}
}

// A typo must name the allowed set. An unknown field that silently returns
// nothing is indistinguishable from a genuine empty answer, which is exactly the
// confusion this command exists to remove.
func TestParseRejectsUnknownFieldsAndNamesTheAllowedSet(t *testing.T) {
	tests := []struct {
		name    string
		args    []string
		wantSub string
	}{
		{"unknown select field", []string{"--select", "id,nope"}, "nope"},
		{"unknown where key", []string{"--where", "colour=red"}, "colour"},
		{"unknown order field", []string{"--order-by", "nope"}, "nope"},
		{"unknown flag", []string{"--verbose"}, "--verbose"},
		{"missing value", []string{"--where"}, "--where"},
		{"negative limit", []string{"--limit", "-1"}, "negative"},
		{"non-numeric limit", []string{"--limit", "many"}, "many"},
		{"non-numeric attempt", []string{"--where", "attempt=lots"}, "lots"},
		{"bad direction", []string{"--order-by", "id,sideways"}, "sideways"},
		{"bad predicate", []string{"--where", "status"}, "status"},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			_, err := Parse(tc.args)
			if err == nil {
				t.Fatalf("Parse(%v) accepted an invalid query", tc.args)
			}
			if !strings.Contains(err.Error(), tc.wantSub) {
				t.Errorf("error %q does not mention %q", err.Error(), tc.wantSub)
			}
		})
	}
}

// The allowed set must actually be listed, otherwise "not queryable" is a dead
// end for the caller.
func TestUnknownFieldListsTheAllowedSet(t *testing.T) {
	_, err := Parse([]string{"--select", "nope"})
	if err == nil {
		t.Fatal("expected an error")
	}
	for _, want := range []string{"status", "kind", "id", "title"} {
		if !strings.Contains(err.Error(), want) {
			t.Errorf("error does not list %q: %s", want, err.Error())
		}
	}
}

func TestRunFiltersByStatus(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)

	rows, err := Run(dir, mustParse(t, "--where", "status=failed"))
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 1 || rows[0].ID != "2" {
		t.Fatalf("got %+v, want only node 2", rows)
	}
	if rows[0].Attempts != 3 {
		t.Errorf("attempts = %d, want 3", rows[0].Attempts)
	}
}

func TestRunFiltersByNumericAttempt(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)

	rows, err := Run(dir, mustParse(t, "--where", "attempt>=2"))
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 2 {
		t.Fatalf("got %d rows, want 2 (nodes 2 and 3)", len(rows))
	}
	for _, r := range rows {
		if r.ID == "1" {
			t.Error("node 1 has 1 attempt and must not match attempt>=2")
		}
	}
}

func TestRunFiltersByArtifactSubstring(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)

	rows, err := Run(dir, mustParse(t, "--where", "artifact=_test.go"))
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 1 || rows[0].ID != "3" {
		t.Fatalf("got %+v, want only the TEST node", rows)
	}
}

func TestRunFiltersByIDGlob(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)

	rows, err := Run(dir, mustParse(t, "--where", "id=*"))
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 3 {
		t.Fatalf("a bare star matched %d rows, want 3", len(rows))
	}
}

// An empty result is an answer: no error, no rows.
func TestRunReturnsNoRowsAndNoErrorWhenNothingMatches(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)

	rows, err := Run(dir, mustParse(t, "--where", "status=skipped"))
	if err != nil {
		t.Fatalf("an empty result must not be an error: %v", err)
	}
	if len(rows) != 0 {
		t.Fatalf("got %d rows, want 0", len(rows))
	}
}

// Ordering must be total, or two identical runs produce two different outputs.
func TestRunOrderingIsDeterministicAndTotal(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)

	// Nodes 2 and 3 share a status? No: they differ. Ordering by role puts the
	// two impl nodes together, where only the id tiebreak can separate them.
	first, err := Run(dir, mustParse(t, "--order-by", "role"))
	if err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 5; i++ {
		again, err := Run(dir, mustParse(t, "--order-by", "role"))
		if err != nil {
			t.Fatal(err)
		}
		for j := range first {
			if first[j].ID != again[j].ID {
				t.Fatalf("order changed between runs at %d: %s vs %s", j, first[j].ID, again[j].ID)
			}
		}
	}
	if first[len(first)-1].ID != "1" {
		t.Errorf("role ordering = %v, want the intent node last", idsOf(first))
	}
}

func TestRunDescendingReversesTheOrder(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)

	asc, err := Run(dir, mustParse(t, "--order-by", "attempts"))
	if err != nil {
		t.Fatal(err)
	}
	desc, err := Run(dir, mustParse(t, "--order-by", "attempts,desc"))
	if err != nil {
		t.Fatal(err)
	}
	if len(asc) != len(desc) {
		t.Fatalf("row count differs: %d vs %d", len(asc), len(desc))
	}
	if asc[0].ID == desc[0].ID && len(asc) > 1 {
		t.Errorf("descending did not reverse: asc=%v desc=%v", idsOf(asc), idsOf(desc))
	}
}

func TestRunLimit(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)

	rows, err := Run(dir, mustParse(t, "--limit", "2"))
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 2 {
		t.Fatalf("got %d rows, want 2", len(rows))
	}
}

// limit 0 is unlimited, not zero rows. Getting this wrong makes the default
// command return nothing.
func TestRunLimitZeroIsUnlimited(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)

	rows, err := Run(dir, mustParse(t))
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 3 {
		t.Fatalf("got %d rows, want all 3", len(rows))
	}
}

// A run that has been planned but never executed has no state.json. Every node
// is pending, which is the truth, and it is not an error.
func TestRunWithNoStateYet(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, "")

	rows, err := Run(dir, mustParse(t))
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 3 {
		t.Fatalf("got %d rows, want 3", len(rows))
	}
	for _, r := range rows {
		if r.Status != "pending" {
			t.Errorf("node %s status = %q, want pending", r.ID, r.Status)
		}
	}
}

func TestRunRejectsADirectoryWithNoPlan(t *testing.T) {
	if _, err := Run(t.TempDir(), mustParse(t)); err == nil {
		t.Fatal("expected an error for a directory with no run.yaml")
	}
}

func TestRenderJSONIsAnArrayAndHonoursSelect(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)
	q := mustParse(t, "--select", "id,status")
	rows, err := Run(dir, q)
	if err != nil {
		t.Fatal(err)
	}

	var buf bytes.Buffer
	if err := Render(&buf, rows, q, true); err != nil {
		t.Fatal(err)
	}
	var decoded []map[string]any
	if err := json.Unmarshal(buf.Bytes(), &decoded); err != nil {
		t.Fatalf("output is not a JSON array: %v\n%s", err, buf.String())
	}
	if len(decoded) != len(rows) {
		t.Fatalf("decoded %d rows, want %d", len(decoded), len(rows))
	}
	for _, row := range decoded {
		if len(row) != 2 {
			t.Errorf("row has %d keys, want 2: %v", len(row), row)
		}
		if _, ok := row["kind"]; ok {
			t.Errorf("select did not project: %v", row)
		}
	}
}

func TestRenderJSONOnAnEmptyResultIsAnEmptyArray(t *testing.T) {
	q := mustParse(t)
	var buf bytes.Buffer
	if err := Render(&buf, nil, q, true); err != nil {
		t.Fatal(err)
	}
	var decoded []map[string]any
	if err := json.Unmarshal(buf.Bytes(), &decoded); err != nil {
		t.Fatalf("empty output is not valid JSON: %v\n%s", err, buf.String())
	}
	if len(decoded) != 0 {
		t.Errorf("got %d rows in the empty array", len(decoded))
	}
}

func TestRenderTableOnAnEmptyResultWritesNothing(t *testing.T) {
	q := mustParse(t)
	var buf bytes.Buffer
	if err := Render(&buf, nil, q, false); err != nil {
		t.Fatal(err)
	}
	if buf.Len() != 0 {
		t.Errorf("an empty table wrote %q, want nothing", buf.String())
	}
}

func TestRenderTableHasAHeader(t *testing.T) {
	dir := t.TempDir()
	writeRun(t, dir, testState)
	q := mustParse(t, "--select", "id,status")
	rows, err := Run(dir, q)
	if err != nil {
		t.Fatal(err)
	}
	var buf bytes.Buffer
	if err := Render(&buf, rows, q, false); err != nil {
		t.Fatal(err)
	}
	out := buf.String()
	if !strings.Contains(out, "ID") || !strings.Contains(out, "STATUS") {
		t.Errorf("table has no header:\n%s", out)
	}
	if !strings.Contains(out, "failed") {
		t.Errorf("table is missing the failed node:\n%s", out)
	}
}

func idsOf(rows []Row) []string {
	out := make([]string, 0, len(rows))
	for _, r := range rows {
		out = append(out, r.ID)
	}
	return out
}
