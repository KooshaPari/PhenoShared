package server

import (
	"fmt"
	"io"
	"net/http"

	"github.com/KooshaPari/dagrun/internal/agents"
	"github.com/KooshaPari/dagrun/internal/applet"
	"github.com/KooshaPari/dagrun/internal/plan"
)

// This file is the applet surface: the two metadata documents and the
// embeddable view a master console mounts. It lives beside server.go rather than
// inside it because the route table, the state loader and the viewer already
// fill that file, and none of this belongs on the same read.
//
// All three are reads. The discovery document says so in words a consumer can
// assert on (authority.writes=false, mount.read_only=true) instead of leaving it
// to be inferred from the absence of a POST route.

// embedCSP is the policy for the embedded page. %s is the frame-ancestors value,
// which is 'self' unless an operator named consumer origins.
//
// default-src 'none' means the page can reach nothing it did not inline: no
// fonts, no images, no remote script. script-src/style-src allow the inline
// block and the inline sheet, connect-src 'self' is the change-detector's poll
// of /api/status, and form-action 'none' makes the "no controls" claim
// mechanical rather than a matter of trust.
const embedCSP = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; " +
	"connect-src 'self'; img-src data:; base-uri 'none'; form-action 'none'; frame-ancestors %s"

// handleAppletManifest serves the contract document and nothing else.
//
// It is separate from /api/applet on purpose: a consumer that only knows
// urn:phenotype:atlas-plan:1:applet must be able to fetch a document valid
// against that schema, and the contract forbids additional properties. Anything
// dagrun-specific would make this route unusable by exactly the tools the
// contract exists for.
func (s *Server) handleAppletManifest(w http.ResponseWriter, r *http.Request) {
	noStore(w)
	writeJSON(w, s.appletManifest)
}

// handleAppletDiscovery serves this instance's own document: the manifest
// unmodified, plus origin, mount, auth and authority.
func (s *Server) handleAppletDiscovery(w http.ResponseWriter, r *http.Request) {
	noStore(w)
	writeJSON(w, applet.NewDiscovery(applet.DiscoveryOptions{
		Version:        s.appletManifest.Version,
		Origin:         originOf(r),
		Addr:           s.Addr(),
		FrameAncestors: s.framePolicy,
	}))
}

// originOf reports the origin the client used, from the request's Host.
//
// It reports http:// unconditionally because this server only ever binds
// loopback and serves plain HTTP. Reading X-Forwarded-Proto instead would let a
// request header describe this server's own scheme, which is how a discovery
// document starts claiming something the deployment does not do. A proxy that
// terminates TLS knows the real origin and should rewrite the document, not ask
// dagrun to guess.
func originOf(r *http.Request) string {
	if r == nil || r.Host == "" {
		return ""
	}
	return "http://" + r.Host
}

// handleEmbed serves the embeddable entrypoint.
func (s *Server) handleEmbed(w http.ResponseWriter, r *http.Request) {
	view, err := s.embedView()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	html, err := applet.RenderEmbed(view)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	h := w.Header()
	h.Set("Content-Type", "text/html; charset=utf-8")
	h.Set("Content-Security-Policy", fmt.Sprintf(embedCSP, s.framePolicy))
	h.Set("X-Content-Type-Options", "nosniff")
	h.Set("Referrer-Policy", "no-referrer")
	noStore(w)
	_, _ = io.WriteString(w, html)
}

// embedView projects the run into the embed page's small model.
//
// Session validation is taken from the agents projection rather than
// re-implemented, so the embed and /api/agents can never disagree about whether
// an id was corroborated. A failure there is not fatal: the cards are an
// optional capability, and losing them means the badge says unvalidated, which
// is the honest reading of "I could not check".
func (s *Server) embedView() (applet.Embed, error) {
	st, err := s.loadState()
	if err != nil {
		return applet.Embed{}, err
	}
	validated := map[string]bool{}
	if doc, err := agents.Build(s.dir, nil); err == nil {
		for _, a := range doc.Agents {
			validated[a.Node] = a.SessionValidated
		}
	}

	// Status cells are ordered by how much of a reader's attention they deserve,
	// then any status this build does not know in sorted order, so the header
	// does not reshuffle between two reads of the same run.
	order := []string{
		plan.StatusRunning, "claimed", plan.StatusFailed, "blocked",
		plan.StatusPending, plan.StatusDone, plan.StatusSkipped, plan.StatusCancelled,
	}
	counts := map[string]int{}

	rows := make([]applet.EmbedNode, 0, len(s.plan.Nodes))
	for _, n := range s.plan.Nodes {
		if n == nil {
			continue
		}
		row := applet.EmbedNode{ID: n.ID, Title: n.Title, Kind: n.Kind, Status: plan.StatusPending}
		if ns := st.Nodes[n.ID]; ns != nil {
			if ns.Status != "" {
				row.Status = ns.Status
			}
			row.Owner = ns.Owner
			row.Session = ns.Session
			row.Validated = ns.Session != "" && validated[n.ID]
			row.Attempts = ns.Attempts
			row.LastError = ns.LastError
			if ns.Verify != nil {
				row.Artifacts = len(ns.Verify.Artifacts)
				for _, a := range ns.Verify.Artifacts {
					if !a.OK {
						row.Missing++
					}
				}
			}
		}
		counts[row.Status]++
		rows = append(rows, row)
	}

	cells := make([]applet.Count, 0, len(counts))
	for _, st := range order {
		if c := counts[st]; c > 0 {
			cells = append(cells, applet.Count{Status: st, Count: c})
			delete(counts, st)
		}
	}
	for _, st := range sortedKeys(counts) {
		cells = append(cells, applet.Count{Status: st, Count: counts[st]})
	}

	return applet.Embed{
		Run:     s.plan.Run,
		Version: s.appletManifest.Version,
		Nodes:   rows,
		Counts:  cells,
		Total:   len(rows),
	}, nil
}

// noStore marks a document that describes live state. A cached applet manifest
// or status page is not merely stale: it is a claim about the present that was
// true in the past.
func noStore(w http.ResponseWriter) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
}

// sortedKeys returns the map's keys in ascending order. The embed view needs a
// deterministic tail for statuses the fixed order does not name, and a map range
// is randomised by design.
func sortedKeys(m map[string]int) []string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	for i := 1; i < len(keys); i++ {
		for j := i; j > 0 && keys[j] < keys[j-1]; j-- {
			keys[j], keys[j-1] = keys[j-1], keys[j]
		}
	}
	return keys
}
