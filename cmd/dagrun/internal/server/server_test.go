package server

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

const testPlan = `version: 1
run: srvtest
nodes:
  - id: "1"
    kind: INTENT
    role: intent
    title: freeze scope
    artifacts: [{path: a.md, min_bytes: 1}]
  - id: "2"
    kind: IMPL
    role: impl
    title: do the work
    artifacts: [{path: b.go, min_bytes: 1}]
`

const testState = `{"version":1,"run":"srvtest","nodes":{
  "1":{"status":"done","attempts":1},
  "2":{"status":"failed","attempts":2,"last_error":"boom"}
}}`

func fixture(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), []byte(testPlan), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "state.json"), []byte(testState), 0o644); err != nil {
		t.Fatal(err)
	}
	return dir
}

func newServer(t *testing.T, dir string) *Server {
	t.Helper()
	s, err := New(Options{Dir: dir})
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func get(t *testing.T, s *Server, path string) (int, string) {
	t.Helper()
	rec := httptest.NewRecorder()
	s.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, path, nil))
	return rec.Code, rec.Body.String()
}

func TestHealthReportsTheRun(t *testing.T) {
	s := newServer(t, fixture(t))
	code, body := get(t, s, "/api/health")
	if code != http.StatusOK {
		t.Fatalf("status = %d, want 200", code)
	}
	var doc map[string]any
	if err := json.Unmarshal([]byte(body), &doc); err != nil {
		t.Fatalf("not JSON: %v", err)
	}
	if doc["run"] != "srvtest" {
		t.Errorf("run = %v, want srvtest", doc["run"])
	}
	if doc["ok"] != true {
		t.Errorf("ok = %v, want true", doc["ok"])
	}
	if !strings.HasPrefix(doc["dir"].(string), "/") {
		t.Errorf("dir should be absolute, got %v", doc["dir"])
	}
}

func TestStatusReflectsTheStateFile(t *testing.T) {
	s := newServer(t, fixture(t))
	code, body := get(t, s, "/api/status")
	if code != http.StatusOK {
		t.Fatalf("status = %d, want 200", code)
	}
	if !strings.Contains(body, `"done"`) || !strings.Contains(body, `"failed"`) {
		t.Errorf("status body does not carry the node states:\n%s", body)
	}
}

// A read against a planned-but-unrun directory is legitimate: every node is
// pending, which is the truth, and it is not an error.
func TestPlannedButUnrunDirectoryServes(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), []byte(testPlan), 0o644); err != nil {
		t.Fatal(err)
	}
	s := newServer(t, dir)
	code, body := get(t, s, "/api/status")
	if code != http.StatusOK {
		t.Fatalf("status = %d, want 200 for an unrun directory", code)
	}
	if strings.Count(body, `"pending"`) != 2 {
		t.Errorf("expected two pending nodes, got:\n%s", body)
	}
}

func TestQueryFiltersAndNamesTheAllowedSet(t *testing.T) {
	s := newServer(t, fixture(t))

	code, body := get(t, s, "/api/query?where=status%3Dfailed&select=id")
	if code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", code, body)
	}
	if !strings.Contains(body, "2") || strings.Contains(body, "1.1") {
		t.Errorf("filter did not narrow to node 2:\n%s", body)
	}

	code, body = get(t, s, "/api/query?where=colour%3Dred")
	if code != http.StatusBadRequest {
		t.Fatalf("unknown field status = %d, want 400", code)
	}
	// query.Parse produces this message; the server must not swallow it,
	// because naming the allowed set is the whole point.
	for _, want := range []string{"colour", "status", "kind"} {
		if !strings.Contains(body, want) {
			t.Errorf("400 body does not mention %q: %s", want, body)
		}
	}
}

func TestQueryJSONMode(t *testing.T) {
	s := newServer(t, fixture(t))
	code, body := get(t, s, "/api/query?where=status%3Ddone&select=id&json=1")
	if code != http.StatusOK {
		t.Fatalf("status = %d", code)
	}
	var rows []map[string]any
	if err := json.Unmarshal([]byte(body), &rows); err != nil {
		t.Fatalf("not a JSON array: %v\n%s", err, body)
	}
	if len(rows) != 1 || rows[0]["id"] != "1" {
		t.Errorf("rows = %v, want exactly node 1", rows)
	}
}

func TestNodeDetailAndMissingNode(t *testing.T) {
	s := newServer(t, fixture(t))

	code, body := get(t, s, "/api/nodes/2")
	if code != http.StatusOK {
		t.Fatalf("status = %d, want 200", code)
	}
	for _, want := range []string{`"id": "2"`, `"status": "failed"`, `"attempts": 2`, "boom"} {
		if !strings.Contains(body, want) {
			t.Errorf("node body missing %q:\n%s", want, body)
		}
	}

	code, body = get(t, s, "/api/nodes/nope")
	if code != http.StatusNotFound {
		t.Fatalf("unknown node status = %d, want 404 (%s)", code, body)
	}
}

func TestRootServesHTMLWithTheReloader(t *testing.T) {
	s := newServer(t, fixture(t))
	code, body := get(t, s, "/")
	if code != http.StatusOK {
		t.Fatalf("status = %d, want 200: %s", code, body)
	}
	if !strings.Contains(body, "srvtest") {
		t.Errorf("viewer HTML does not mention the run")
	}
	if !strings.Contains(body, "/api/status") {
		t.Errorf("viewer HTML has no reloader script")
	}
}

// The server publishes a run directory with no auth, so a non-loopback bind is
// refused rather than trusted.
func TestNewRefusesANonLoopbackAddress(t *testing.T) {
	for _, addr := range []string{"0.0.0.0:8080", "192.168.1.10:8080", ":8080"} {
		// ":8080" has an empty host, which means all interfaces. It must be
		// refused for the same reason as 0.0.0.0.
		_, err := New(Options{Dir: fixture(t), Addr: addr})
		if err == nil {
			t.Errorf("addr %q was accepted; it must be refused", addr)
		}
	}
}

func TestNewAcceptsLoopbackForms(t *testing.T) {
	for _, addr := range []string{"127.0.0.1:0", "localhost:9999", "[::1]:0"} {
		if _, err := New(Options{Dir: fixture(t), Addr: addr}); err != nil {
			t.Errorf("loopback addr %q was refused: %v", addr, err)
		}
	}
}

func TestNewRequiresAPlan(t *testing.T) {
	_, err := New(Options{Dir: t.TempDir()})
	if err == nil {
		t.Fatal("expected an error for a directory with no run.yaml")
	}
	if !strings.Contains(err.Error(), "dagrun plan") {
		t.Errorf("error should name the command that installs a plan: %v", err)
	}
}

// A corrupt state file must yield a 500, never a panic: a monitor must not be
// able to take the process down.
func TestCorruptStateIsA500NotAPanic(t *testing.T) {
	dir := fixture(t)
	if err := os.WriteFile(filepath.Join(dir, "state.json"), []byte("{not json"), 0o644); err != nil {
		t.Fatal(err)
	}
	s := newServer(t, dir)
	st := s.Handler()

	rec := httptest.NewRecorder()
	// A panic here would propagate out of ServeHTTP and fail the test process,
	// which is exactly what the recover wrapper must prevent.
	st.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/api/status", nil))
	if rec.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500", rec.Code)
	}
}

// The server is read-only: a request must not create or modify the state file.
func TestReadDoesNotWrite(t *testing.T) {
	dir := fixture(t)
	path := filepath.Join(dir, "state.json")
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	s := newServer(t, dir)
	for _, p := range []string{"/api/status", "/api/plan", "/api/nodes/1", "/", "/api/query"} {
		get(t, s, p)
	}
	after, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if string(before) != string(after) {
		t.Error("a read modified state.json; the server must never write")
	}
}

func TestListenBindsAndStopsOnContext(t *testing.T) {
	s := newServer(t, fixture(t))
	ctx, cancel := context.WithCancel(context.Background())

	done := make(chan error, 1)
	go func() { done <- s.Listen(ctx) }()

	// Wait for the bind. The sleep matters: a tight loop never yields to the
	// Listen goroutine, so it would spin out its whole budget before the bind
	// could happen.
	for i := 0; s.Addr() == ""; i++ {
		if i > 200 {
			t.Fatal("Listen never bound an address")
		}
		time.Sleep(5 * time.Millisecond)
	}

	addr := s.Addr()
	if !strings.HasPrefix(addr, "127.0.0.1:") {
		t.Errorf("bound %q, want a loopback address", addr)
	}

	resp, err := http.Get("http://" + addr + "/api/health")
	if err != nil {
		t.Fatalf("GET /api/health: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("status = %d", resp.StatusCode)
	}

	cancel()
	if err := <-done; err != nil {
		t.Errorf("Listen returned %v on a clean cancel, want nil", err)
	}
}
