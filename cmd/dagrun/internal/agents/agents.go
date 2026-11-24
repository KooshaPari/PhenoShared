// Package agents projects a run into agent cards: one card per node that has
// actually run, bound to the child harness session that executed it.
//
// This is the read-only half of a console. It answers "who is working on what,
// and how do I know" from the run directory alone, without opening the store
// for writing and without touching a terminal screen.
//
// The projection never upgrades an unknown to a fact. A node whose harness
// printed no session id gets an empty Session; one whose id cannot be found in
// the harness's own artifact store is reported unvalidated with the evidence
// string saying so.
package agents

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/session"
	"github.com/KooshaPari/dagrun/internal/store"
)

// Agent is one card: a node, the identity that ran it, and what happened.
type Agent struct {
	Node  string `json:"node"`
	Title string `json:"title,omitempty"`

	Status string `json:"status"`
	Owner  string `json:"owner,omitempty"`

	Harness  string `json:"harness,omitempty"`
	Provider string `json:"provider,omitempty"`
	Model    string `json:"model,omitempty"`

	Session          string `json:"session,omitempty"`
	SessionSource    string `json:"session_source,omitempty"`
	SessionValidated bool   `json:"session_validated"`
	SessionEvidence  string `json:"session_evidence,omitempty"`

	Attempts   int    `json:"attempts,omitempty"`
	StartedAt  string `json:"started_at,omitempty"`
	FinishedAt string `json:"finished_at,omitempty"`
	ElapsedMS  int64  `json:"elapsed_ms,omitempty"`
	LastError  string `json:"last_error,omitempty"`
}

// Doc is the whole card set for one run.
type Doc struct {
	Run         string `json:"run"`
	Dir         string `json:"dir,omitempty"`
	GeneratedAt string `json:"generated_at"`
	// ReadOnly is always true: this document is an observation surface.
	ReadOnly bool `json:"read_only"`
	// Self is the process that asked for the document, when the caller had
	// one. It is the orchestrator card, not a node card.
	Self   *session.Card  `json:"self,omitempty"`
	Agents []Agent        `json:"agents"`
	Counts map[string]int `json:"counts"`
	// Unknown records what the projection itself could not establish.
	Unknown []string `json:"unknown,omitempty"`
}

// Build reads a run directory the same way the read-only server does: run.yaml
// and state.json directly, with no store lock and no writes.
func Build(dir string, self *session.Card) (*Doc, error) {
	abs, err := filepath.Abs(dir)
	if err != nil {
		return nil, err
	}
	raw, err := os.ReadFile(filepath.Join(abs, "run.yaml"))
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("no plan installed at %s; run `dagrun plan FILE` first", abs)
		}
		return nil, err
	}
	p, err := plan.Parse(raw)
	if err != nil {
		return nil, err
	}

	st := &store.State{Run: p.Run, Nodes: map[string]*store.NodeState{}}
	stateRaw, err := os.ReadFile(filepath.Join(abs, "state.json"))
	switch {
	case err == nil:
		if err := json.Unmarshal(stateRaw, &st); err != nil {
			return nil, fmt.Errorf("corrupt state in %s: %w", abs, err)
		}
		if st.Nodes == nil {
			st.Nodes = map[string]*store.NodeState{}
		}
	case os.IsNotExist(err):
		// A planned-but-unrun directory is legitimate: every node is pending
		// and no card claims an identity.
	default:
		return nil, err
	}

	home, _ := os.UserHomeDir()
	validate := func(harness, id string) (string, bool) {
		return validateNodeSession(home, harness, id)
	}
	doc := BuildFrom(p, st, self, validate)
	doc.Dir = abs
	return doc, nil
}

// BuildFrom is the pure projection, which is what the tests exercise.
func BuildFrom(p *plan.Plan, st *store.State, self *session.Card, validate func(harness, id string) (string, bool)) *Doc {
	d := &Doc{
		GeneratedAt: time.Now().UTC().Format(time.RFC3339),
		ReadOnly:    true,
		Self:        self,
		Agents:      []Agent{},
		Counts:      map[string]int{},
	}
	if p != nil {
		d.Run = p.Run
	}
	if st != nil && st.Run != "" && d.Run == "" {
		d.Run = st.Run
	}

	var nodes []*plan.Node
	if p != nil {
		for _, n := range p.Nodes {
			if n != nil && n.ID != "" {
				nodes = append(nodes, n)
			}
		}
	}
	sort.SliceStable(nodes, func(i, j int) bool { return plan.Less(nodes[i].ID, nodes[j].ID) })

	now := time.Now()
	for _, n := range nodes {
		var ns *store.NodeState
		if st != nil {
			ns = st.Nodes[n.ID]
		}
		if !hasRun(ns) {
			continue
		}
		d.Agents = append(d.Agents, cardOf(n, ns, validate, now))
	}

	for _, a := range d.Agents {
		d.Counts[a.Status]++
	}
	if st != nil && len(st.Nodes) > len(d.Agents) {
		d.Unknown = append(d.Unknown,
			fmt.Sprintf("%d node(s) are in state.json but are no longer in the plan", len(st.Nodes)-len(d.Agents)))
	}
	return d
}

// hasRun reports whether a state entry shows that work was attempted. A card is
// only worth showing once something actually ran: a pending node with no owner
// and no session is the graph's job, not the card list's.
func hasRun(ns *store.NodeState) bool {
	if ns == nil {
		return false
	}
	return !ns.StartedAt.IsZero() || ns.Owner != "" || ns.Session != "" ||
		ns.Status == plan.StatusRunning || ns.Status == plan.StatusDone || ns.Status == plan.StatusFailed
}

func cardOf(n *plan.Node, ns *store.NodeState, validate func(harness, id string) (string, bool), now time.Time) Agent {
	a := Agent{
		Node:     n.ID,
		Title:    n.Title,
		Status:   plan.StatusPending,
		Harness:  n.Harness,
		Provider: n.Provider,
		Model:    n.Model,
	}
	if ns == nil {
		return a
	}
	if ns.Status != "" {
		a.Status = ns.Status
	}
	a.Owner = ns.Owner
	a.Attempts = ns.Attempts
	a.LastError = ns.LastError
	a.Session = ns.Session
	a.SessionSource = ns.SessionSource
	if !ns.StartedAt.IsZero() {
		a.StartedAt = ns.StartedAt.UTC().Format(time.RFC3339)
	}
	if !ns.FinishedAt.IsZero() {
		a.FinishedAt = ns.FinishedAt.UTC().Format(time.RFC3339)
	}
	switch {
	case ns.DurationMS > 0:
		a.ElapsedMS = ns.DurationMS
	case !ns.StartedAt.IsZero():
		a.ElapsedMS = now.Sub(ns.StartedAt).Milliseconds()
	}
	// The usage object is a better source than the plan for what actually ran:
	// "auto" resolves to a real provider, and a model can be chosen at runtime.
	if ns.Usage != nil {
		if ns.Usage.Provider != "" {
			a.Provider = ns.Usage.Provider
		}
		if ns.Usage.Model != "" {
			a.Model = ns.Usage.Model
		}
	}

	if a.Session != "" {
		if validate != nil {
			evidence, ok := validate(a.Harness, a.Session)
			a.SessionValidated = ok
			a.SessionEvidence = evidence
		}
		if !a.SessionValidated && a.SessionEvidence == "" {
			a.SessionEvidence = "no on-disk artifact names this id"
		}
	}
	return a
}

// validateNodeSession tries the declared harness first, then the harnesses that
// have a known artifact store. The fallback matters because plan.Harness is
// often "auto": the plan does not know which family actually ran.
func validateNodeSession(home, harness, id string) (string, bool) {
	if ev, ok := session.ValidateArtifact(home, harness, id); ok {
		return ev, true
	}
	var firstEvidence string
	for _, alt := range []string{"kcode", "jcode", "codex"} {
		if alt == harness {
			continue
		}
		ev, ok := session.ValidateArtifact(home, alt, id)
		if ok {
			return ev, true
		}
		if firstEvidence == "" && ev != "" {
			firstEvidence = ev
		}
	}
	if firstEvidence == "" {
		firstEvidence = "no on-disk artifact names this id"
	}
	return firstEvidence, false
}
