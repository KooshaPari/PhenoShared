package server

// The read routes. Every handler here answers a GET from the run directory and
// writes nothing, which is why they share a file separate from the listener in
// server.go: the boundary between "serves facts" and "owns a socket" is worth
// keeping visible.

import (
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"

	"github.com/KooshaPari/dagrun/internal/agents"
	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/query"
	"github.com/KooshaPari/dagrun/internal/viz"
)

// handleFallback renders the viewer for a page request and refuses a typo'd
// machine path.
//
// Without this, an unmatched path such as /api/servers, a route that has never
// existed, falls through to the viewer and answers 200 text/html. A program then
// cannot tell "no such route" from "here is a page": it parses markup as data,
// or treats a silent wrong answer as a working call. Measured as a real
// confusion during launcher work, which is why the refusal is here rather than
// left to a caller's own validation.
func (s *Server) handleFallback(w http.ResponseWriter, r *http.Request) {
	if isMachinePath(r.URL.Path) {
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.WriteHeader(http.StatusNotFound)
		_, _ = io.WriteString(w, `{"error":"no such route","path":`+strconv.Quote(r.URL.Path)+"}\n")
		return
	}
	s.handleViz(w, r)
}

// isMachinePath reports whether a path sits in a namespace a program reads, where
// an HTML answer is always a mistake. Page paths return false on purpose: a
// browser asking for an unknown page should still get the viewer.
func isMachinePath(p string) bool {
	return strings.HasPrefix(p, "/api/") || strings.HasPrefix(p, "/.well-known/")
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

// handleAgents serves the agent-card projection: one card per node that has
// run, with the child session id and whether it could be validated.
//
// It is built from run.yaml and state.json directly, like every other route
// here, so the monitor still does not sit on the store's write path.
func (s *Server) handleAgents(w http.ResponseWriter, r *http.Request) {
	doc, err := agents.Build(s.dir, nil)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	writeJSON(w, doc)
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
			// Session identity is reported as recorded: the id and how it was
			// learned. Validation lives in /api/agents, which has the home
			// directory and the harness artifact stores to check against.
			if ns.Session != "" {
				doc["session"] = ns.Session
				doc["session_source"] = ns.SessionSource
			}
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
