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

	"github.com/KooshaPari/dagrun/internal/applet"
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
	// filepath.IsAbs, not a leading "/": on Windows an absolute path starts
	// with a drive letter (C:\...), so the unix-only check failed there.
	if !filepath.IsAbs(doc["dir"].(string)) {
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

// The viewer and the JSON API must report the same identity. They share one
// projection (agents.BuildFrom) precisely so a page cannot quietly disagree
// with /api/agents, and this test is what keeps that true.
func TestRootAndAgentsAgreeOnSession(t *testing.T) {
	const id = "dz-no-such-session-0001"
	dir := fixture(t)
	state := `{"version":1,"run":"srvtest","nodes":{
  "1":{"status":"done","attempts":1,"session":"` + id + `","session_source":"stdout"},
  "2":{"status":"failed","attempts":2,"last_error":"boom"}
}}`
	if err := os.WriteFile(filepath.Join(dir, "state.json"), []byte(state), 0o644); err != nil {
		t.Fatal(err)
	}
	s := newServer(t, dir)

	code, body := get(t, s, "/api/agents")
	if code != http.StatusOK {
		t.Fatalf("/api/agents status = %d: %s", code, body)
	}
	var api struct {
		ReadOnly bool `json:"read_only"`
		Agents   []struct {
			Node             string `json:"node"`
			Session          string `json:"session"`
			SessionValidated bool   `json:"session_validated"`
		} `json:"agents"`
	}
	if err := json.Unmarshal([]byte(body), &api); err != nil {
		t.Fatalf("/api/agents is not JSON: %v", err)
	}
	if !api.ReadOnly {
		t.Error("/api/agents is not marked read-only")
	}
	var found bool
	for _, a := range api.Agents {
		if a.Session != id {
			continue
		}
		found = true
		if a.SessionValidated {
			t.Errorf("session %q was reported validated; it cannot be corroborated", id)
		}
	}
	if !found {
		t.Fatalf("/api/agents does not carry session %q: %s", id, body)
	}

	code, page := get(t, s, "/")
	if code != http.StatusOK {
		t.Fatalf("/ status = %d: %s", code, page)
	}
	for _, want := range []string{id, `"agents"`, `"self"`} {
		if !strings.Contains(page, want) {
			t.Errorf("viewer HTML does not carry %q; the page and the API disagree", want)
		}
	}
}

// --- applet surface ---------------------------------------------------------

// newServerWith builds a server with options, for the tests that need a version
// or an embed allow-list.
func newServerWith(t *testing.T, dir string, tweak func(*Options)) *Server {
	t.Helper()
	opt := Options{Dir: dir}
	if tweak != nil {
		tweak(&opt)
	}
	s, err := New(opt)
	if err != nil {
		t.Fatal(err)
	}
	return s
}

func TestAppletManifestIsContractValid(t *testing.T) {
	s := newServerWith(t, fixture(t), func(o *Options) { o.Version = "9.9.9-test" })
	code, body := get(t, s, applet.ContractPath)
	if code != http.StatusOK {
		t.Fatalf("%s status = %d: %s", applet.ContractPath, code, body)
	}

	// Decoded strictly: the contract forbids additional properties, so a key the
	// package does not model is a conformance failure, not extra information.
	dec := json.NewDecoder(strings.NewReader(body))
	dec.DisallowUnknownFields()
	var m applet.Manifest
	if err := dec.Decode(&m); err != nil {
		t.Fatalf("manifest does not decode strictly: %v\n%s", err, body)
	}
	if err := m.Validate(); err != nil {
		t.Fatalf("published manifest does not validate: %v", err)
	}
	if m.ID != applet.ID || m.Version != "9.9.9-test" {
		t.Errorf("manifest id/version = %q/%q, want %q/9.9.9-test", m.ID, m.Version, applet.ID)
	}
	if m.Synthetic {
		t.Error("published manifest is marked synthetic; this is a live server")
	}
}

func TestAppletManifestIsNeverCached(t *testing.T) {
	s := newServer(t, fixture(t))
	rec := httptest.NewRecorder()
	s.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, applet.ContractPath, nil))
	if got := rec.Header().Get("Cache-Control"); got != "no-store" {
		t.Errorf("Cache-Control = %q, want no-store: a cached manifest is a claim about the present that was true in the past", got)
	}
}

func TestAppletDiscoveryNamesTheMountAndTheAuthority(t *testing.T) {
	s := newServerWith(t, fixture(t), func(o *Options) { o.Version = "1.0.0" })
	code, body := get(t, s, "/api/applet")
	if code != http.StatusOK {
		t.Fatalf("/api/applet status = %d: %s", code, body)
	}
	var d applet.Discovery
	if err := json.Unmarshal([]byte(body), &d); err != nil {
		t.Fatalf("discovery is not JSON: %v\n%s", err, body)
	}
	if d.Contract != applet.Contract {
		t.Errorf("contract = %q, want %q", d.Contract, applet.Contract)
	}
	if err := d.Applet.Validate(); err != nil {
		t.Errorf("embedded manifest does not validate: %v", err)
	}
	if !d.Mount.ReadOnly || d.Mount.Path != "/embed" {
		t.Errorf("mount = %+v, want a read-only /embed", d.Mount)
	}
	if d.Authority.Writes || d.Authority.Owner != "dagrun" {
		t.Errorf("authority = %+v, want dagrun owning and not writing", d.Authority)
	}
	if !d.Host.Loopback {
		t.Error("host.loopback = false")
	}
	if d.Host.Origin != "http://example.com" {
		// httptest's default Host. The point is that the origin is derived from
		// the request rather than invented or guessed from a proxy header.
		t.Errorf("host.origin = %q, want the request's origin", d.Host.Origin)
	}
	if d.Mount.FramePolicy != applet.SameOriginFrames {
		t.Errorf("frame policy = %q, want the same-origin default", d.Mount.FramePolicy)
	}
}

func TestEmbedIsAnObserverThatCannotBeFramedElsewhere(t *testing.T) {
	s := newServer(t, fixture(t))
	rec := httptest.NewRecorder()
	s.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/embed", nil))
	if rec.Code != http.StatusOK {
		t.Fatalf("/embed status = %d: %s", rec.Code, rec.Body.String())
	}
	csp := rec.Header().Get("Content-Security-Policy")
	if csp == "" {
		t.Fatal("/embed has no CSP; an unauthenticated surface must state its framing policy")
	}
	for _, want := range []string{"frame-ancestors 'self'", "default-src 'none'", "form-action 'none'"} {
		if !strings.Contains(csp, want) {
			t.Errorf("CSP is missing %q: %s", want, csp)
		}
	}
	if got := rec.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Errorf("X-Content-Type-Options = %q, want nosniff", got)
	}

	body := rec.Body.String()
	// The run's nodes are there, with their recorded statuses.
	for _, want := range []string{
		`data-node="1"`, `data-node="2"`, `data-status="done"`, `data-status="failed"`,
		"freeze scope", "do the work", "boom", "srvtest",
	} {
		if !strings.Contains(body, want) {
			t.Errorf("/embed is missing %q", want)
		}
	}
	// And it offers no way to act: a second console must not become a control
	// surface for an agent.
	for _, banned := range []string{"<button", "<form", "<input", "<textarea", "<select"} {
		if strings.Contains(body, banned) {
			t.Errorf("/embed contains %q", banned)
		}
	}
}

func TestEmbedAllowOriginWidensThePolicyOnlyWhenAsked(t *testing.T) {
	s := newServerWith(t, fixture(t), func(o *Options) {
		o.EmbedAllowOrigins = []string{"https://console.example:8443"}
	})
	rec := httptest.NewRecorder()
	s.Handler().ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/embed", nil))
	want := "frame-ancestors 'self' https://console.example:8443"
	if csp := rec.Header().Get("Content-Security-Policy"); !strings.Contains(csp, want) {
		t.Fatalf("CSP = %q, want it to contain %q", csp, want)
	}
	// The discovery publishes the same effective policy, so a console can decide
	// whether to mount without parsing a header from a page it has not fetched.
	_, body := get(t, s, "/api/applet")
	var d applet.Discovery
	if err := json.Unmarshal([]byte(body), &d); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(d.Mount.FramePolicy, "https://console.example:8443") {
		t.Errorf("mount.frame_policy = %q, want it to name the allowed origin", d.Mount.FramePolicy)
	}
}

func TestEmbedAllowOriginRefusesAWildcard(t *testing.T) {
	for _, bad := range []string{"*", "https://*.example.com", "https://x/y", ""} {
		_, err := New(Options{Dir: fixture(t), EmbedAllowOrigins: []string{bad}})
		if err == nil {
			t.Errorf("New accepted --embed-allow-origin %q", bad)
		}
	}
}

func TestEmbedReportsAnUncorroboratedSessionAsUnvalidated(t *testing.T) {
	dir := t.TempDir()
	planYAML := "version: 1\nrun: embedrun\nnodes:\n  - id: \"1\"\n    kind: IMPL\n    role: impl\n    title: work\n"
	stateJSON := `{"version":1,"run":"embedrun","nodes":{"1":{"status":"running","owner":"jcode",` +
		`"session":"no-such-session-id","session_source":"harness"}}}`
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), []byte(planYAML), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "state.json"), []byte(stateJSON), 0o644); err != nil {
		t.Fatal(err)
	}
	s, err := New(Options{Dir: dir})
	if err != nil {
		t.Fatal(err)
	}
	code, body := get(t, s, "/embed")
	if code != http.StatusOK {
		t.Fatalf("/embed status = %d: %s", code, body)
	}
	if !strings.Contains(body, "no-such-session-id") {
		t.Fatalf("/embed dropped the recorded session id: %s", body)
	}
	if !strings.Contains(body, "(unvalidated)") {
		t.Errorf("/embed presents an uncorroborated session id as fact: %s", body)
	}
}
