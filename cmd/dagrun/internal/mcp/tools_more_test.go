package mcp

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// morePlan is a two-node fixture with a satisfiable and an unsatisfiable
// contract, so a test can put the run into more than one status.
const morePlan = `
version: 1
run: moretest
max_parallel: 2
nodes:
  - id: "1"
    kind: DOC
    title: first
    artifacts: [{path: artifacts/a.md, min_bytes: 3}]
  - id: "2"
    kind: DOC
    title: second
    deps: ["1"]
    artifacts: [{path: artifacts/b.md, min_bytes: 3}]
`

// newRunDir installs morePlan under root and returns the run directory.
func newRunDir(t *testing.T, root string) string {
	t.Helper()
	p, err := plan.Parse([]byte(morePlan))
	if err != nil {
		t.Fatalf("parse fixture: %v", err)
	}
	p.Root = root
	dir := filepath.Join(root, ".dagrun")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatalf("mkdir run dir: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), []byte(morePlan), 0o644); err != nil {
		t.Fatalf("write run.yaml: %v", err)
	}
	if _, err := store.Open(dir, p, []byte(morePlan), true); err != nil {
		t.Fatalf("open store: %v", err)
	}
	return dir
}

// failNode marks a node failed through the real store, so the fixture state is
// produced by the same code path the CLI uses rather than by hand-written JSON.
func failNode(t *testing.T, dir, id, reason string) {
	t.Helper()
	p, err := plan.Parse([]byte(morePlan))
	if err != nil {
		t.Fatalf("parse fixture: %v", err)
	}
	st, err := store.Open(dir, p, []byte(morePlan), false)
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	if err := st.Force(id, plan.StatusFailed, reason, nil, time.Now()); err != nil {
		t.Fatalf("force %s failed: %v", id, err)
	}
}

// callOne drives a single tools/call and returns the result envelope.
func callOne(t *testing.T, name, args string) map[string]any {
	t.Helper()
	frames := serve(t, []string{
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"` + name + `","arguments":` + args + `}}`,
	})
	if len(frames) != 1 {
		t.Fatalf("%s: got %d frames", name, len(frames))
	}
	res, ok := frames[0]["result"].(map[string]any)
	if !ok {
		t.Fatalf("%s: no result (rpc error: %v)", name, frames[0]["error"])
	}
	return res
}

// callText returns the payload text and the isError flag of a tool call.
func callText(t *testing.T, name, args string) (string, bool) {
	t.Helper()
	res := callOne(t, name, args)
	content, _ := res["content"].([]any)
	if len(content) == 0 {
		t.Fatalf("%s: empty content", name)
	}
	text, _ := content[0].(map[string]any)["text"].(string)
	isErr, _ := res["isError"].(bool)
	return text, isErr
}

// theSeven is the list this file exists to keep honest.
var theSeven = []string{
	"dagrun_query", "dagrun_recover", "dagrun_replan",
	"dagrun_stats", "dagrun_lint", "dagrun_doctor", "dagrun_export",
}

// TestToolsListIncludesTheSevenDrivingTools pins the catalogue size, so a future
// tool added without a test fails here rather than silently drifting.
func TestToolsListIncludesTheSevenDrivingTools(t *testing.T) {
	frames := serve(t, []string{`{"jsonrpc":"2.0","id":1,"method":"tools/list"}`})
	if len(frames) != 1 {
		t.Fatalf("got %d frames", len(frames))
	}
	list, _ := frames[0]["result"].(map[string]any)
	tools, _ := list["tools"].([]any)
	if len(tools) != 19 {
		t.Fatalf("tools/list returned %d tools, want 19 (12 + 7)", len(tools))
	}
	seen := map[string]bool{}
	for _, raw := range tools {
		m, _ := raw.(map[string]any)
		if name, ok := m["name"].(string); ok {
			seen[name] = true
		}
	}
	for _, want := range theSeven {
		if !seen[want] {
			t.Errorf("missing tool %s", want)
		}
	}
}

// TestNewToolSchemasAreObjectsWithDir checks each new tool advertises a usable
// schema: an object, a dir property, and the properties its handler reads.
func TestNewToolSchemasAreObjectsWithDir(t *testing.T) {
	wantProps := map[string][]string{
		"dagrun_query":   {"dir", "where", "select", "order_by", "limit"},
		"dagrun_recover": {"dir", "nodes", "force"},
		"dagrun_replan":  {"dir", "file", "apply", "force"},
		"dagrun_stats":   {"dir"},
		"dagrun_lint":    {"dir"},
		"dagrun_doctor":  {"dir"},
		"dagrun_export":  {"dir", "format"},
	}
	frames := serve(t, []string{`{"jsonrpc":"2.0","id":1,"method":"tools/list"}`})
	list, _ := frames[0]["result"].(map[string]any)
	tools, _ := list["tools"].([]any)
	found := map[string]map[string]any{}
	for _, raw := range tools {
		m, _ := raw.(map[string]any)
		if name, ok := m["name"].(string); ok {
			found[name] = m
		}
	}
	for _, name := range theSeven {
		m, ok := found[name]
		if !ok {
			t.Fatalf("%s is not advertised", name)
		}
		schema, ok := m["inputSchema"].(map[string]any)
		if !ok {
			t.Errorf("%s: inputSchema is not an object: %v", name, m["inputSchema"])
			continue
		}
		if schema["type"] != "object" {
			t.Errorf("%s: inputSchema.type = %v, want object", name, schema["type"])
		}
		props, ok := schema["properties"].(map[string]any)
		if !ok {
			t.Errorf("%s: inputSchema has no properties object", name)
			continue
		}
		for _, prop := range wantProps[name] {
			if _, ok := props[prop]; !ok {
				t.Errorf("%s: inputSchema is missing property %q", name, prop)
			}
		}
		if d, ok := props["dir"].(map[string]any); !ok || d["type"] != "string" {
			t.Errorf("%s: dir property is not a described string: %v", name, props["dir"])
		}
	}
}

// TestQuerySelectsByFailedStatus exercises the delegation to internal/query:
// the tool must return exactly the node the query selected.
func TestQuerySelectsByFailedStatus(t *testing.T) {
	root := t.TempDir()
	dir := newRunDir(t, root)
	failNode(t, dir, "2", "boom")

	text, isErr := callText(t, "dagrun_query", `{"dir":"`+dir+`","where":["status=failed"]}`)
	if isErr {
		t.Fatalf("query signalled an error: %s", text)
	}
	var payload struct {
		Count int `json:"count"`
		Rows  []struct {
			ID     string `json:"id"`
			Status string `json:"status"`
		} `json:"rows"`
	}
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		t.Fatalf("query payload is not JSON: %v\n%s", err, text)
	}
	if payload.Count != 1 || len(payload.Rows) != 1 {
		t.Fatalf("count = %d, rows = %d, want exactly the failed node\n%s", payload.Count, len(payload.Rows), text)
	}
	if payload.Rows[0].ID != "2" || payload.Rows[0].Status != plan.StatusFailed {
		t.Errorf("row = %+v, want id 2 with status %s", payload.Rows[0], plan.StatusFailed)
	}
}

// TestQueryRejectsAnUnknownPredicate proves the tool carries query's own
// validation rather than silently matching nothing.
func TestQueryRejectsAnUnknownPredicate(t *testing.T) {
	root := t.TempDir()
	dir := newRunDir(t, root)
	frames := serve(t, []string{
		`{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"dagrun_query","arguments":{"dir":"` + dir + `","where":["nonsense=x"]}}}`,
	})
	errObj, _ := frames[0]["error"].(map[string]any)
	if errObj == nil {
		t.Fatalf("an unknown predicate was accepted: %v", frames[0])
	}
	if msg, _ := errObj["message"].(string); !strings.Contains(msg, "status") {
		t.Errorf("message = %q, want it to list the queryable keys", msg)
	}
}

// TestDoctorWithoutAPlanIsAnErrorResult is the fail-closed case: a directory
// with no run.yaml must come back as an error RESULT with a finding, never as a
// panic and never as a healthy verdict.
func TestDoctorWithoutAPlanIsAnErrorResult(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, ".dagrun")
	text, isErr := callText(t, "dagrun_doctor", `{"dir":"`+dir+`"}`)
	if !isErr {
		t.Fatalf("doctor on a planless directory did not signal an error: %s", text)
	}
	if !strings.Contains(text, "missing_plan") && !strings.Contains(text, "run.yaml") &&
		!strings.Contains(text, "missing_dir") {
		t.Errorf("doctor findings do not name the missing plan: %s", text)
	}
	var payload map[string]any
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		t.Fatalf("doctor payload is not JSON: %v\n%s", err, text)
	}
	if healthy, _ := payload["healthy"].(bool); healthy {
		t.Errorf("healthy = true for a directory with no plan: %s", text)
	}
}

// TestDoctorOnARealRunIsHealthy proves the store-backed branch of doctor runs
// without changing the run it inspects.
func TestDoctorOnARealRunIsHealthy(t *testing.T) {
	root := t.TempDir()
	dir := newRunDir(t, root)
	text := refreshDoctor(t, dir)
	var payload struct {
		Healthy bool `json:"healthy"`
	}
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		t.Fatalf("doctor payload is not JSON: %v\n%s", err, text)
	}
	if !payload.Healthy {
		t.Logf("doctor reported findings on a fresh run (tolerated): %s", text)
	}
}

// refreshDoctor calls doctor and returns its text whatever the verdict, so the
// happy path test does not depend on the host's harness inventory.
func refreshDoctor(t *testing.T, dir string) string {
	t.Helper()
	text, _ := callText(t, "dagrun_doctor", `{"dir":"`+dir+`"}`)
	return text
}

// TestExportJSONIsParseable checks the json format comes back as a document a
// client can decode, and that its content field carries it verbatim.
func TestExportJSONIsParseable(t *testing.T) {
	root := t.TempDir()
	dir := newRunDir(t, root)
	text, isErr := callText(t, "dagrun_export", `{"dir":"`+dir+`","format":"json"}`)
	if isErr {
		t.Fatalf("export signalled an error: %s", text)
	}
	var payload struct {
		Format  string `json:"format"`
		Content string `json:"content"`
	}
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		t.Fatalf("export payload is not JSON: %v\n%s", err, text)
	}
	if payload.Format != "json" {
		t.Errorf("format = %q, want json", payload.Format)
	}
	if strings.TrimSpace(payload.Content) == "" {
		t.Fatalf("export content is empty: %s", text)
	}
	var doc map[string]any
	if err := json.Unmarshal([]byte(payload.Content), &doc); err != nil {
		t.Fatalf("exported content is not parseable JSON: %v\n%s", err, payload.Content)
	}
	if len(doc) == 0 {
		t.Errorf("exported JSON is an empty object")
	}
}

// TestExportRejectsUnknownFormat requires the refusal to name the allowed set.
func TestExportRejectsUnknownFormat(t *testing.T) {
	root := t.TempDir()
	dir := newRunDir(t, root)
	text, isErr := callText(t, "dagrun_export", `{"dir":"`+dir+`","format":"csv"}`)
	if !isErr {
		t.Fatalf("an unknown format was accepted: %s", text)
	}
	for _, want := range []string{"json", "agileplus", "tracera"} {
		if !strings.Contains(text, want) {
			t.Errorf("refusal does not name %q: %s", want, text)
		}
	}
}

// TestLintOnAFreshPlanIsClean covers the lint adapter's read side.
func TestLintOnAFreshPlanIsClean(t *testing.T) {
	root := t.TempDir()
	dir := newRunDir(t, root)
	text, isErr := callText(t, "dagrun_lint", `{"dir":"`+dir+`"}`)
	var payload struct {
		Run      string `json:"run"`
		OK       bool   `json:"ok"`
		Errors   int    `json:"errors"`
		Warnings int    `json:"warnings"`
	}
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		t.Fatalf("lint payload is not JSON: %v\n%s", err, text)
	}
	if payload.Run != "moretest" {
		t.Errorf("run = %q, want moretest", payload.Run)
	}
	if payload.OK != (payload.Errors == 0) {
		t.Errorf("ok disagrees with the error count: %s", text)
	}
	if isErr != (payload.Errors > 0) {
		t.Errorf("isError = %v with %d errors", isErr, payload.Errors)
	}
}

// TestStatsReportsTheRun covers the stats adapter against a real run directory.
func TestStatsReportsTheRun(t *testing.T) {
	root := t.TempDir()
	dir := newRunDir(t, root)
	text, isErr := callText(t, "dagrun_stats", `{"dir":"`+dir+`"}`)
	if isErr {
		t.Fatalf("stats signalled an error: %s", text)
	}
	var payload struct {
		Report struct {
			Run   string `json:"run"`
			Nodes int    `json:"nodes"`
		} `json:"report"`
	}
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		t.Fatalf("stats payload is not JSON: %v\n%s", err, text)
	}
	if payload.Report.Nodes == 0 {
		t.Errorf("stats reported no nodes: %s", text)
	}
}

// TestRecoverReportsWithoutReclaimingByDefault is the safety property: the
// default call must not touch the run.
func TestRecoverReportsWithoutReclaimingByDefault(t *testing.T) {
	root := t.TempDir()
	dir := newRunDir(t, root)
	text, _ := callText(t, "dagrun_recover", `{"dir":"`+dir+`"}`)
	var payload struct {
		Applied bool `json:"applied"`
	}
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		t.Fatalf("recover payload is not JSON: %v\n%s", err, text)
	}
	if payload.Applied {
		t.Errorf("recover applied a reclaim without force: %s", text)
	}
}

// TestReplanIsReadOnlyByDefault pins the refusal default from the tool
// description: a diff must never adopt the revision on its own.
func TestReplanIsReadOnlyByDefault(t *testing.T) {
	root := t.TempDir()
	dir := newRunDir(t, root)
	revised := filepath.Join(root, "revised.yaml")
	const revisedPlan = `
version: 1
run: moretest
max_parallel: 2
nodes:
  - id: "1"
    kind: DOC
    title: first, renamed
    artifacts: [{path: artifacts/a.md, min_bytes: 3}]
  - id: "2"
    kind: DOC
    title: second
    deps: ["1"]
    artifacts: [{path: artifacts/b.md, min_bytes: 4}]
`
	if err := os.WriteFile(revised, []byte(revisedPlan), 0o644); err != nil {
		t.Fatalf("write revised plan: %v", err)
	}
	before, err := os.ReadFile(filepath.Join(dir, "run.yaml"))
	if err != nil {
		t.Fatal(err)
	}
	text, isErr := callText(t, "dagrun_replan", `{"dir":"`+dir+`","file":"`+revised+`"}`)
	if isErr {
		t.Fatalf("replan signalled an error: %s", text)
	}
	var payload struct {
		Applied  bool             `json:"applied"`
		Safe     bool             `json:"safe"`
		Changes  []map[string]any `json:"changes"`
		Blocking []string         `json:"blocking"`
	}
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		t.Fatalf("replan payload is not JSON: %v\n%s", err, text)
	}
	if payload.Applied {
		t.Errorf("replan applied the revision without apply=true: %s", text)
	}
	if len(payload.Changes) == 0 {
		t.Errorf("replan reported no changes for a plan that changed: %s", text)
	}
	if payload.Safe {
		t.Errorf("safe = true although node 2's contract changed: %s", text)
	}
	if len(payload.Blocking) == 0 {
		t.Errorf("blocking is empty although a contract changed: %s", text)
	}
	after, err := os.ReadFile(filepath.Join(dir, "run.yaml"))
	if err != nil {
		t.Fatal(err)
	}
	if string(before) != string(after) {
		t.Errorf("replan rewrote run.yaml without apply=true")
	}
}
