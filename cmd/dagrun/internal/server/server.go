// Package server exposes a running dagrun as a local read-only HTTP surface.
//
// Two jobs, one server, because they are the same data:
//
//   - the LIVE viz panel. `dagrun viz` writes one static file; a file cannot
//     show a run that is still moving. Here the HTML is rendered per request and
//     the page re-renders itself when the state changes.
//   - a small JSON API an agent or a monitoring tool can read, so "what is
//     running" does not require a shell round trip and a human eyeball.
//
// It is READ-ONLY by construction. There is no route that claims a node, takes
// a lease, or writes a file, and it does not open the store at all: it reads
// run.yaml and state.json directly. That is deliberate. A monitor must not sit on
// the write path, and the simplest way to guarantee that is to give it no way to
// write.
package server

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/query"
	"github.com/KooshaPari/dagrun/internal/store"
	"github.com/KooshaPari/dagrun/internal/viz"
)

// DefaultAddr is loopback with an ephemeral port. Anything else has to be asked
// for explicitly, because this surface has no authentication.
const DefaultAddr = "127.0.0.1:0"

// Options configures the server.
type Options struct {
	// Dir is the run directory holding run.yaml, state.json and trace/.
	Dir string
	// Addr is the listen address. Must be loopback.
	Addr string
}

// Server serves one run directory.
type Server struct {
	dir string
	// addr is set by Listen. Before that it holds the requested value.
	addr string
	// errOut receives panic reports. Defaults to os.Stderr.
	errOut io.Writer
	plan   *plan.Plan

	// mu guards the bound fields below. They are written by Listen and read by
	// callers that need the port before the serve loop starts, which is a
	// different goroutine, so an unsynchronised pair here would be a race.
	mu        sync.Mutex
	bound     bool
	boundAddr string
	// ln is the bound listener, created by Bind and consumed by Listen.
	ln net.Listener
}

// New validates the request without binding anything.
//
// It refuses a non-loopback address rather than trusting a caller to mean well:
// this server publishes a run directory with no auth, so "0.0.0.0" is not a
// preference, it is an incident.
func New(opt Options) (*Server, error) {
	dir := opt.Dir
	if strings.TrimSpace(dir) == "" {
		dir = ".dagrun"
	}
	abs, err := filepath.Abs(dir)
	if err != nil {
		return nil, err
	}

	addr := opt.Addr
	if strings.TrimSpace(addr) == "" {
		addr = DefaultAddr
	}
	if err := requireLoopback(addr); err != nil {
		return nil, err
	}

	raw, err := os.ReadFile(filepath.Join(abs, "run.yaml"))
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("no run at %s; install one with `dagrun plan FILE --dir %s`", abs, dir)
		}
		return nil, err
	}
	p, err := plan.Parse(raw)
	if err != nil {
		return nil, fmt.Errorf("parse %s/run.yaml: %w", abs, err)
	}

	return &Server{dir: abs, addr: addr, errOut: os.Stderr, plan: p}, nil
}

// requireLoopback accepts localhost, 127.0.0.0/8 and ::1 only.
func requireLoopback(addr string) error {
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		return fmt.Errorf("addr %q is not host:port: %w", addr, err)
	}
	// An empty host (":8080") means every interface, so it is the one case that
	// looks loopback-ish and is the opposite. Refuse it.
	if host == "" {
		return fmt.Errorf("addr %q has no host, which binds every interface: name 127.0.0.1 explicitly", addr)
	}
	if strings.EqualFold(host, "localhost") {
		return nil
	}
	if ip := net.ParseIP(host); ip != nil && ip.IsLoopback() {
		return nil
	}
	return fmt.Errorf("addr %q is not loopback: this server serves a run directory with no authentication, so it binds 127.0.0.1 (or ::1) only", addr)
}

// Addr is the bound address once Listen has bound it, otherwise "".
func (s *Server) Addr() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.bound {
		return s.boundAddr
	}
	return ""
}

// Handler returns the route table.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/health", s.recover(s.handleHealth))
	mux.HandleFunc("/api/plan", s.recover(s.handlePlan))
	mux.HandleFunc("/api/status", s.recover(s.handleStatus))
	mux.HandleFunc("/api/query", s.recover(s.handleQuery))
	mux.HandleFunc("/api/nodes/", s.recover(s.handleNode))
	mux.HandleFunc("/", s.recover(s.handleViz))
	return mux
}

// Bind creates the listener and records the real address, without serving yet.
//
// It exists so a caller can print the URL BEFORE blocking in Listen. A ready
// line published after Listen returns is published when the server stops, which
// tells nobody anything; doing it in two steps is the only honest way to report
// an ephemeral port.
func (s *Server) Bind() error {
	if s.ln != nil {
		return nil
	}
	ln, err := net.Listen("tcp", s.addr)
	if err != nil {
		return err
	}
	s.ln = ln
	s.mu.Lock()
	s.bound = true
	s.boundAddr = ln.Addr().String()
	s.mu.Unlock()
	return nil
}

// Listen binds (if Bind was not called) and serves until ctx is cancelled.
func (s *Server) Listen(ctx context.Context) error {
	if err := s.Bind(); err != nil {
		return err
	}
	ln := s.ln

	srv := &http.Server{Handler: s.Handler(), ReadHeaderTimeout: 10 * time.Second}
	errc := make(chan error, 1)
	go func() {
		err := srv.Serve(ln)
		if errors.Is(err, http.ErrServerClosed) {
			err = nil
		}
		errc <- err
	}()

	select {
	case <-ctx.Done():
		shutCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutCtx)
		return nil
	case err := <-errc:
		return err
	}
}

// recover turns a panic into a 500. A monitoring endpoint must never be able to
// take the process down, and a corrupt state file is exactly the kind of input
// that would otherwise do it.
func (s *Server) recover(h func(http.ResponseWriter, *http.Request)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if v := recover(); v != nil {
				fmt.Fprintf(s.errOut, "server: panic serving %s: %v\n", r.URL.Path, v)
				http.Error(w, "internal error", http.StatusInternalServerError)
			}
		}()
		h(w, r)
	}
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]any{"ok": true, "dir": s.dir, "run": s.plan.Run})
}

func (s *Server) handlePlan(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, s.plan)
}

func (s *Server) handleStatus(w http.ResponseWriter, r *http.Request) {
	st, err := s.loadState()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	writeJSON(w, st)
}

// handleQuery translates the request into the query package's own argument
// form, so the grammar has exactly one implementation.
func (s *Server) handleQuery(w http.ResponseWriter, r *http.Request) {
	qv := r.URL.Query()
	var args []string
	for _, where := range qv["where"] {
		args = append(args, "--where", where)
	}
	if sel := qv["select"]; len(sel) > 0 {
		args = append(args, "--select", strings.Join(sel, ","))
	}
	if ob := qv.Get("order_by"); ob != "" {
		args = append(args, "--order-by", ob)
	}
	if lim := qv.Get("limit"); lim != "" {
		args = append(args, "--limit", lim)
	}

	q, err := query.Parse(args)
	if err != nil {
		// query.Parse names the allowed set, which is the whole point of
		// surfacing it rather than returning an empty list.
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	rows, err := query.Run(s.dir, q)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	if qv.Get("json") == "1" {
		w.Header().Set("Content-Type", "application/json")
		_ = query.Render(w, rows, q, true)
		return
	}
	var buf strings.Builder
	if err := query.Render(&buf, rows, q, false); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	_, _ = io.WriteString(w, buf.String())
}

// handleNode answers for one node: plan fields, its state record, and its
// artifact results.
func (s *Server) handleNode(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/api/nodes/")
	if id == "" {
		http.Error(w, "usage: /api/nodes/{id}", http.StatusBadRequest)
		return
	}
	var node *plan.Node
	for _, n := range s.plan.Nodes {
		if n != nil && n.ID == id {
			node = n
			break
		}
	}
	if node == nil {
		http.Error(w, fmt.Sprintf("no node %q in this run", id), http.StatusNotFound)
		return
	}

	doc := map[string]any{
		"id": node.ID, "kind": node.Kind, "role": node.Role, "title": node.Title,
		"status": plan.StatusPending,
	}
	if st, err := s.loadState(); err == nil {
		if ns := st.Nodes[id]; ns != nil {
			doc["status"] = ns.Status
			doc["owner"] = ns.Owner
			doc["attempts"] = ns.Attempts
			doc["last_error"] = ns.LastError
			if ns.Verify != nil {
				doc["artifacts"] = ns.Verify.Artifacts
			}
		}
	}
	writeJSON(w, doc)
}

// handleViz renders the interactive viewer fresh, with a small reloader.
//
// The reloader is a full page reload, not an incremental patch: the renderer is
// a canvas app holding its own state, and re-rendering it wholesale is both
// simpler and less likely to be wrong than reaching into it. A DAG of a few
// hundred nodes renders in milliseconds, so the crude version is the honest one.
func (s *Server) handleViz(w http.ResponseWriter, r *http.Request) {
	doc, err := viz.Build(s.dir)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	html, err := viz.RenderHTML(doc)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	out := injectReloader(string(html))
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	_, _ = io.WriteString(w, out)
}

// reloaderScript reloads the page only when /api/status actually changed, so an
// idle run does not repaint every two seconds and lose the reader's scroll.
const reloaderScript = `<script>
(function () {
  var last = null;
  function tick() {
    fetch('/api/status', {cache: 'no-store'})
      .then(function (r) { return r.text(); })
      .then(function (t) {
        if (last !== null && t !== last) { location.reload(); return; }
        last = t;
      })
      .catch(function () { /* a reload failure must not spam the console */ })
      .then(function () { setTimeout(tick, 2000); });
  }
  setTimeout(tick, 2000);
})();
</script>
`

func injectReloader(html string) string {
	if i := strings.LastIndex(html, "</body>"); i >= 0 {
		return html[:i] + reloaderScript + html[i:]
	}
	return html + reloaderScript
}

// loadState reads the state document without opening the store, because
// store.Open can create directories and a fresh state and this server must not
// write anything.
func (s *Server) loadState() (*store.State, error) {
	raw, err := os.ReadFile(filepath.Join(s.dir, "state.json"))
	if err != nil {
		if os.IsNotExist(err) {
			// A planned-but-unrun directory is a legitimate state: every node is
			// pending, which is the truth.
			st := &store.State{Run: s.plan.Run, Nodes: map[string]*store.NodeState{}}
			for _, n := range s.plan.Nodes {
				if n != nil {
					st.Nodes[n.ID] = &store.NodeState{Status: plan.StatusPending}
				}
			}
			return st, nil
		}
		return nil, err
	}
	var st store.State
	if err := json.Unmarshal(raw, &st); err != nil {
		return nil, fmt.Errorf("corrupt state in %s: %w", s.dir, err)
	}
	if st.Nodes == nil {
		st.Nodes = map[string]*store.NodeState{}
	}
	return &st, nil
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	_ = enc.Encode(v)
}
