package agents

import (
	"strings"
	"testing"
	"time"

	"github.com/KooshaPari/dagrun/internal/harness"
	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/session"
	"github.com/KooshaPari/dagrun/internal/store"
)

func testPlan() *plan.Plan {
	return &plan.Plan{
		Run: "demo",
		Nodes: []*plan.Node{
			{ID: "1.1", Kind: "IMPL", Title: "first", Harness: "jcode", Provider: "auto", Model: "auto"},
			{ID: "1.2", Kind: "IMPL", Title: "second", Harness: "codex", Provider: "openai", Model: "gpt-6.1-terra"},
		},
	}
}

func noEvidence(harness, id string) (string, bool) { return "", false }

// A node that has not run is the graph's business, not a card: pending work
// with no owner and no session must not appear as an agent.
func TestBuildFromSkipsNodesThatNeverRan(t *testing.T) {
	st := &store.State{Run: "demo", Nodes: map[string]*store.NodeState{
		"1.2": {Status: plan.StatusPending},
	}}
	doc := BuildFrom(testPlan(), st, nil, noEvidence)

	if len(doc.Agents) != 0 {
		t.Fatalf("got %d cards for never-run nodes: %+v", len(doc.Agents), doc.Agents)
	}
	if !doc.ReadOnly {
		t.Error("the projection is an observation surface and must be read-only")
	}
}

func TestBuildFromCardShape(t *testing.T) {
	st := &store.State{Run: "demo", Nodes: map[string]*store.NodeState{
		"1.1": {
			Status:   plan.StatusDone,
			Owner:    "agent-1",
			Attempts: 2,
			Session:  "sess-1",
			// The plan asked for "auto"; the harness resolved a real runner at
			// runtime, and that is what the card must show.
			Usage: &harness.Usage{Provider: "opencode-go", Model: "deepseek-v4.1-flash"},
		},
	}}
	doc := BuildFrom(testPlan(), st, nil, noEvidence)

	if len(doc.Agents) != 1 {
		t.Fatalf("got %d cards, want 1", len(doc.Agents))
	}
	a := doc.Agents[0]
	if a.Node != "1.1" || a.Status != plan.StatusDone || a.Title != "first" {
		t.Fatalf("card = %+v", a)
	}
	if a.Provider != "opencode-go" || a.Model != "deepseek-v4.1-flash" {
		t.Errorf("runtime runner not preferred over the plan: %q/%q", a.Provider, a.Model)
	}
	if a.Session != "sess-1" || a.SessionSource != "" {
		t.Errorf("session = (%q, %q)", a.Session, a.SessionSource)
	}
	if a.SessionValidated {
		t.Error("a session with no on-disk evidence must not report validated")
	}
	if !strings.Contains(a.SessionEvidence, "no on-disk artifact") {
		t.Errorf("evidence = %q", a.SessionEvidence)
	}
	if doc.Counts[plan.StatusDone] != 1 {
		t.Errorf("counts = %v", doc.Counts)
	}
}

func TestBuildFromValidationIsEvidenceBacked(t *testing.T) {
	st := &store.State{Run: "demo", Nodes: map[string]*store.NodeState{
		"1.2": {Status: plan.StatusRunning, Owner: "agent-2", Session: "thread-9"},
	}}
	validate := func(harness, id string) (string, bool) {
		return "artifact:/home/u/.codex/sessions/2026/11/24/rollout-thread-9.jsonl", id == "thread-9"
	}
	doc := BuildFrom(testPlan(), st, nil, validate)

	a := doc.Agents[0]
	if !a.SessionValidated {
		t.Fatal("a corroborated id must report validated")
	}
	if !strings.HasPrefix(a.SessionEvidence, "artifact:") {
		t.Errorf("evidence = %q", a.SessionEvidence)
	}
}

// A state entry that the plan no longer contains is a gap worth naming, not a
// card to invent.
func TestBuildFromNamesNodesMissingFromThePlan(t *testing.T) {
	st := &store.State{Run: "demo", Nodes: map[string]*store.NodeState{
		"1.1":     {Status: plan.StatusDone, Owner: "a"},
		"deleted": {Status: plan.StatusDone, Owner: "b"},
	}}
	doc := BuildFrom(testPlan(), st, nil, noEvidence)

	if len(doc.Agents) != 1 {
		t.Fatalf("got %d cards, want only the planned node", len(doc.Agents))
	}
	if len(doc.Unknown) == 0 || !strings.Contains(strings.Join(doc.Unknown, " "), "no longer in the plan") {
		t.Errorf("unknown = %v, want the orphaned state entry named", doc.Unknown)
	}
}

// Elapsed time is a measurement: the recorded duration wins, and a node with
// no recorded duration but a start time is measured against the clock.
func TestBuildFromElapsedTime(t *testing.T) {
	started := time.Now().Add(-90 * time.Second)
	st := &store.State{Run: "demo", Nodes: map[string]*store.NodeState{
		"1.1": {Status: plan.StatusRunning, Owner: "a", StartedAt: started},
		"1.2": {Status: plan.StatusDone, Owner: "b", StartedAt: started, DurationMS: 1234},
	}}
	doc := BuildFrom(testPlan(), st, nil, noEvidence)

	byNode := map[string]Agent{}
	for _, a := range doc.Agents {
		byNode[a.Node] = a
	}
	if got := byNode["1.2"].ElapsedMS; got != 1234 {
		t.Errorf("recorded duration ignored: %d", got)
	}
	if got := byNode["1.1"].ElapsedMS; got < 89_000 {
		t.Errorf("running node elapsed = %d, want ~90s", got)
	}
}

// The self card is the orchestrator that asked, not a node, so it must be
// carried through unchanged and never counted.
func TestBuildFromCarriesSelfCard(t *testing.T) {
	self := &session.Card{Host: "orch", Harness: "jcode"}
	doc := BuildFrom(testPlan(), &store.State{Run: "demo"}, self, noEvidence)
	if doc.Self != self {
		t.Error("self card was dropped or copied")
	}
	if len(doc.Agents) != 0 || len(doc.Counts) != 0 {
		t.Errorf("self card leaked into the node cards: %+v", doc.Agents)
	}
}
