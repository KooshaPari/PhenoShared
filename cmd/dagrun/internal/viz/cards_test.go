package viz

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/KooshaPari/dagrun/internal/agents"
	"github.com/KooshaPari/dagrun/internal/session"
)

// cardsPlan is a two-node run where one node recorded a harness session. The
// id is deliberately one no host can have on disk, so validation is testable
// without touching $HOME.
const cardsPlan = `version: 1
run: cards-fixture
nodes:
  - id: "1"
    kind: INTENT
    title: freeze scope
    artifacts: [{path: a.md, min_bytes: 1}]
  - id: "2"
    kind: IMPL
    title: do the work
    artifacts: [{path: b.md, min_bytes: 1}]
`

const cardsState = `{"version":1,"run":"cards-fixture","nodes":{
  "1":{"status":"done","attempts":1},
  "2":{"status":"running","attempts":1,"session":"dz-no-such-session-0000","session_source":"stdout"}
}}`

func cardsRun(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), []byte(cardsPlan), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "state.json"), []byte(cardsState), 0o644); err != nil {
		t.Fatal(err)
	}
	return dir
}

// A rendered page must carry the same cards /api/agents serves, so opening the
// viewer is enough to see who ran a node; no second request, no second
// identity implementation.
func TestBuildAttachesOneCardPerNode(t *testing.T) {
	doc, err := Build(cardsRun(t))
	if err != nil {
		t.Fatalf("Build: %v", err)
	}
	if len(doc.Agents) != len(doc.Nodes) {
		t.Fatalf("cards = %d, nodes = %d; want one card per node", len(doc.Agents), len(doc.Nodes))
	}
	seen := map[string]agents.Agent{}
	for _, c := range doc.Agents {
		seen[c.Node] = c
	}
	for _, n := range doc.Nodes {
		if _, ok := seen[n.ID]; !ok {
			t.Errorf("no card for node %q", n.ID)
		}
	}
	if got := seen["2"].Session; got != "dz-no-such-session-0000" {
		t.Errorf("card 2 session = %q, want the id the executor recorded", got)
	}
	if seen["2"].SessionSource != "stdout" {
		t.Errorf("card 2 session_source = %q, want stdout", seen["2"].SessionSource)
	}
	if doc.Self == nil {
		t.Fatal("document has no self card; the page cannot say which observer rendered it")
	}
	if !doc.Self.ReadOnly {
		t.Error("self card is not marked read-only")
	}
}

// An id nobody can corroborate stays unvalidated. The console must never
// promote a claim to a fact, which is the defect this field exists to prevent.
func TestCardsDoNotUpgradeAnUncorroboratedSession(t *testing.T) {
	doc, err := Build(cardsRun(t))
	if err != nil {
		t.Fatalf("Build: %v", err)
	}
	for _, c := range doc.Agents {
		if c.Node != "2" {
			continue
		}
		if c.SessionValidated {
			t.Fatalf("session %q was reported validated; no artifact can exist for it", c.Session)
		}
		if c.SessionEvidence == "" {
			t.Error("unvalidated card carries no evidence field explaining why")
		}
	}
}

// Cards builds on a plan and state the document already holds, so the pure
// projection must not invent identities when the caller gave it none.
func TestFromDoesNotInventCards(t *testing.T) {
	p, nodes, snap, events := tinyRun(t)
	doc := From(p, nodes, snap, events)
	if len(doc.Agents) != 0 {
		t.Fatalf("From attached %d cards; the pure projection must not read the host", len(doc.Agents))
	}
	if doc.Self != nil {
		t.Fatal("From attached a self card; the pure projection must not read the host")
	}
}

// Cards copies; a later change to the source must not rewrite a rendered page.
func TestCardsCopiesTheCardSet(t *testing.T) {
	src := &agents.Doc{
		ReadOnly: true,
		Agents:   []agents.Agent{{Node: "1", Session: "abc"}},
		Unknown:  []string{"one thing"},
		Self:     &session.Card{ReadOnly: true, PID: 42},
	}
	d := &Doc{}
	d.Cards(src)

	src.Agents[0].Session = "changed"
	src.Unknown[0] = "changed"

	if d.Agents[0].Session != "abc" {
		t.Errorf("doc card session = %q, want abc; the card set must be copied", d.Agents[0].Session)
	}
	if d.Unknown[0] != "one thing" {
		t.Errorf("doc unknown = %q, want the original", d.Unknown[0])
	}
	if d.Self == nil || d.Self.PID != 42 {
		t.Error("self card was not carried over")
	}
}

// A nil source is a legitimate state (a document built before cards existed)
// and must not panic or blank the document.
func TestCardsWithNilSourceIsANoOp(t *testing.T) {
	d := &Doc{Run: "keep-me"}
	d.Cards(nil)
	if d.Run != "keep-me" {
		t.Errorf("run = %q; attaching a nil card set must not touch the document", d.Run)
	}
	var nilDoc *Doc
	nilDoc.Cards(&agents.Doc{}) // must not panic
}

// The viewer reads cards from the embedded JSON, so the wire format matters as
// much as the struct.
func TestRenderHTMLCarriesTheCards(t *testing.T) {
	doc, err := Build(cardsRun(t))
	if err != nil {
		t.Fatalf("Build: %v", err)
	}
	html, err := RenderHTML(doc)
	if err != nil {
		t.Fatalf("RenderHTML: %v", err)
	}
	var wire struct {
		Agents []agents.Agent `json:"agents"`
		Self   *session.Card  `json:"self"`
	}
	if err := json.Unmarshal(extractData(t, html), &wire); err != nil {
		t.Fatalf("embedded document is not valid JSON: %v", err)
	}
	if len(wire.Agents) != len(doc.Nodes) {
		t.Fatalf("embedded cards = %d, want %d", len(wire.Agents), len(doc.Nodes))
	}
	if wire.Self == nil {
		t.Error("embedded document has no self card")
	}
	if !strings.Contains(string(html), "dz-no-such-session-0000") {
		t.Error("embedded document does not carry the node session id")
	}
}

// The page must still render for a caller that supplied no cards, because
// RenderHTML is also used on documents built by hand.
func TestRenderHTMLWithoutCardsStillRenders(t *testing.T) {
	p, nodes, snap, events := tinyRun(t)
	html, err := RenderHTML(From(p, nodes, snap, events))
	if err != nil {
		t.Fatalf("RenderHTML: %v", err)
	}
	if len(html) == 0 {
		t.Fatal("rendered HTML is empty")
	}
}
