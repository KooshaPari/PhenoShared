package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/KooshaPari/dagrun/internal/agents"
	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/session"
	"github.com/KooshaPari/dagrun/internal/store"
)

// `dagrun agents` is the console's read side: it must project a claimed node
// into a card that names the session that ran it, and it must say out loud
// that a card built without evidence is unvalidated.
func TestCmdAgentsProjectsClaimedNode(t *testing.T) {
	root := t.TempDir()
	t.Chdir(root)
	runDir := filepath.Join(root, ".dagrun")

	planBody := `version: 1
run: console-cards
intent: prove agent cards come from state
nodes:
  - id: "1.1"
    kind: IMPL
    title: build the thing
    harness: jcode
    check: echo ok
`
	planPath := filepath.Join(root, "plan.yaml")
	if err := os.WriteFile(planPath, []byte(planBody), 0o644); err != nil {
		t.Fatalf("write plan: %v", err)
	}
	if err := cmdPlan([]string{"--dir", runDir, planPath}); err != nil {
		t.Fatalf("plan: %v", err)
	}
	if err := cmdClaim([]string{"--dir", runDir, "--owner", "agent-1", "1.1"}); err != nil {
		t.Fatalf("claim: %v", err)
	}

	// Record a session id the way the executor does, then read the card back.
	p, err := plan.Parse([]byte(planBody))
	if err != nil {
		t.Fatalf("parse plan: %v", err)
	}
	st, err := store.Open(runDir, p, []byte(planBody), false)
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	if ok, err := st.RecordSession("1.1", "agent-1", 1, "sess-abc", "stdout:session_id"); err != nil || !ok {
		t.Fatalf("record session: ok=%v err=%v", ok, err)
	}

	out := captureStdout(t, func() {
		if err := cmdAgents([]string{"--dir", runDir, "--json"}); err != nil {
			t.Fatalf("agents: %v", err)
		}
	})

	var doc agents.Doc
	if err := json.Unmarshal([]byte(out), &doc); err != nil {
		t.Fatalf("not JSON: %v\n%s", err, out)
	}
	if doc.Run != "console-cards" {
		t.Errorf("run = %q", doc.Run)
	}
	if !doc.ReadOnly {
		t.Error("the card document must declare itself read-only")
	}
	if len(doc.Agents) != 1 {
		t.Fatalf("got %d cards, want 1: %s", len(doc.Agents), out)
	}
	a := doc.Agents[0]
	if a.Node != "1.1" || a.Session != "sess-abc" || a.SessionSource != "stdout:session_id" {
		t.Fatalf("card = %+v", a)
	}
	// The fake id exists in no harness store, so the card must refuse to call
	// it validated.
	if a.SessionValidated {
		t.Errorf("unverifiable session reported as validated: %+v", a)
	}
	if !strings.Contains(a.SessionEvidence, "no on-disk artifact") {
		t.Errorf("evidence = %q", a.SessionEvidence)
	}
}

// A planned-but-unrun run is legitimate: the command must report an empty card
// set rather than failing or inventing identities.
func TestCmdAgentsUnrunPlanHasNoCards(t *testing.T) {
	root := t.TempDir()
	t.Chdir(root)
	runDir := filepath.Join(root, ".dagrun")
	planPath := filepath.Join(root, "plan.yaml")
	body := "version: 1\nrun: fresh\nnodes:\n  - id: \"1.1\"\n    kind: IMPL\n    title: t\n    check: echo ok\n"
	if err := os.WriteFile(planPath, []byte(body), 0o644); err != nil {
		t.Fatalf("write plan: %v", err)
	}
	if err := cmdPlan([]string{"--dir", runDir, planPath}); err != nil {
		t.Fatalf("plan: %v", err)
	}

	out := captureStdout(t, func() {
		if err := cmdAgents([]string{"--dir", runDir}); err != nil {
			t.Fatalf("agents: %v", err)
		}
	})
	if !strings.Contains(out, "no node has run yet") {
		t.Errorf("unrun plan output = %q", out)
	}
	if strings.Contains(out, "session ") {
		t.Errorf("unrun plan invented a session: %q", out)
	}
}

// `dagrun session` must answer "who am I" without a run directory, and must
// keep a claim and its evidence separate.
func TestCmdSessionAnswersWithoutARun(t *testing.T) {
	dir := t.TempDir()
	t.Chdir(dir)

	out := captureStdout(t, func() {
		if err := cmdSession(nil); err != nil {
			t.Fatalf("session: %v", err)
		}
	})
	if !strings.Contains(out, "harness") || !strings.Contains(out, "pid") {
		t.Errorf("session output lacks the identity sections: %q", out)
	}

	out = captureStdout(t, func() {
		if err := cmdSession([]string{"--json"}); err != nil {
			t.Fatalf("session --json: %v", err)
		}
	})
	var card session.Card
	if err := json.Unmarshal([]byte(out), &card); err != nil {
		t.Fatalf("not JSON: %v\n%s", err, out)
	}
	if !card.ReadOnly || card.PID <= 0 {
		t.Errorf("card = %+v", card)
	}
	if card.SessionID != "" && !card.SessionValidated && card.SessionEvidence == "" {
		t.Error("an unvalidated session must carry the reason it is unvalidated")
	}
}

// captureStdout runs fn with stdout redirected and returns what it wrote.
func captureStdout(t *testing.T, fn func()) string {
	t.Helper()
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatalf("pipe: %v", err)
	}
	old := os.Stdout
	os.Stdout = w
	done := make(chan string, 1)
	go func() {
		var sb strings.Builder
		buf := make([]byte, 4096)
		for {
			n, err := r.Read(buf)
			sb.Write(buf[:n])
			if err != nil {
				break
			}
		}
		done <- sb.String()
	}()
	fn()
	w.Close()
	os.Stdout = old
	return <-done
}
