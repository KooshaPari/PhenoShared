package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/KooshaPari/dagrun/internal/agents"
)

// cmdAgents prints the agent-card projection of a run: one card per node that
// actually ran, bound to the child harness session that executed it.
//
// It is read-only and lock-free, reading run.yaml and state.json directly the
// way `dagrun serve` does. A monitor that sat on the write path would be a
// second source of truth; this is a projection, not a participant.
func cmdAgents(args []string) error {
	if hasHelp(args) {
		fmt.Fprint(os.Stdout, `usage: dagrun agents [--dir DIR] [--json]

Print one agent card per node that has run.

  --dir DIR   run directory (default .dagrun)
  --json      machine-readable document on stdout

A card reports the node, its status, the harness/provider/model that ran it, and
the child session id the harness printed. session_validated is true only when an
artifact in the harness's own store names that id; it is never inferred.
`)
		return nil
	}

	var dir string
	var jsonOut bool
	fs := flagSet("agents", &dir, &jsonOut)
	if err := fs.Parse(args); err != nil {
		return err
	}

	self := resolveSelf(time.Now())
	doc, err := agents.Build(dir, &self)
	if err != nil {
		return err
	}

	if jsonOut {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		return enc.Encode(doc)
	}

	fmt.Printf("run %s   dir %s   cards %d   (read-only)\n", orDash(doc.Run), orDash(doc.Dir), len(doc.Agents))
	if len(doc.Counts) > 0 {
		var parts []string
		for _, st := range []string{"running", "done", "failed", "pending", "skipped"} {
			if doc.Counts[st] > 0 {
				parts = append(parts, fmt.Sprintf("%s %d", st, doc.Counts[st]))
			}
		}
		if len(parts) > 0 {
			fmt.Printf("  %s\n", strings.Join(parts, "  "))
		}
	}
	fmt.Println()
	if len(doc.Agents) == 0 {
		fmt.Println("no node has run yet")
		return nil
	}
	for _, a := range doc.Agents {
		fmt.Printf("%-28s %-8s %s\n", a.Node, a.Status, agentLine(a))
	}
	if len(doc.Unknown) > 0 {
		fmt.Println()
		for _, u := range doc.Unknown {
			fmt.Printf("unknown: %s\n", u)
		}
	}
	return nil
}

// agentLine renders the identity part of a card on one line: which agent ran
// the node, and how certain that identity is.
func agentLine(a agents.Agent) string {
	var parts []string
	if a.Harness != "" {
		parts = append(parts, a.Harness)
	}
	m := a.Model
	if a.Provider != "" {
		if m != "" {
			m = a.Provider + "/" + m
		} else {
			m = a.Provider
		}
	}
	if m != "" {
		parts = append(parts, m)
	}
	switch {
	case a.Session == "":
		parts = append(parts, "session UNKNOWN")
	case a.SessionValidated:
		parts = append(parts, "session "+a.Session+" (validated)")
	default:
		parts = append(parts, "session "+a.Session+" (unvalidated)")
	}
	if a.Attempts > 1 {
		parts = append(parts, fmt.Sprintf("attempts %d", a.Attempts))
	}
	if a.ElapsedMS > 0 {
		parts = append(parts, (time.Duration(a.ElapsedMS) * time.Millisecond).Round(time.Second).String())
	}
	if a.LastError != "" {
		parts = append(parts, "error: "+oneLine(a.LastError, 80))
	}
	return strings.Join(parts, "  ")
}

// oneLine bounds a multi-line error so a card stays one line.
func oneLine(s string, max int) string {
	s = strings.Join(strings.Fields(s), " ")
	if len(s) <= max {
		return s
	}
	return s[:max-1] + "…"
}
