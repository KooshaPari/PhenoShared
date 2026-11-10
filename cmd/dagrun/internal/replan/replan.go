// Package replan installs a revised plan over an existing run without losing
// the work the run already verified.
//
// The logic used to live in cmd_replan.go, where only the CLI could reach it.
// An MCP client that wants to rewrite a live run needs the same guarantees the
// CLI has, so the mutation is lifted here and the CLI becomes a thin wrapper
// that prints the report and delegates the write.
//
// The division of labour stays where internal/plan put it:
//
//	plan.Diff        structural: what changed between the two plans
//	AgainstDone      run-aware: which verified results the revision would drop
//	Apply (here)     the only place that mutates state, and it refuses to
//	                 discard verified work unless it is forced
package replan

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// Result is what applying a revised plan did.
type Result struct {
	Changes   []plan.NodeChange `json:"changes"`
	Kept      []string          `json:"kept"`
	Discarded []string          `json:"discarded"`
	Blocking  []string          `json:"blocking,omitempty"`
}

// planFile is the installed plan inside a run directory.
const planFile = "run.yaml"

// Apply installs a revised plan for an existing run, carrying forward the
// completions whose contract did not change.
//
// force=false refuses when a node that is currently DONE would be discarded.
//
// rawPlanBytes is the exact document to install; it is hashed for the state and
// then written verbatim, so the bytes on disk and the recorded hash cannot
// drift. The caller parses and validates the revision, because a package that
// both validated and applied would have two places to report a bad plan.
func Apply(dir string, revised *plan.Plan, rawPlanBytes []byte, force bool) (*Result, error) {
	if revised == nil {
		return nil, fmt.Errorf("replan: no revised plan supplied")
	}

	// The revision is diffed against the plan that is actually installed, not
	// against whatever the caller believes is installed.
	installedRaw, err := os.ReadFile(filepath.Join(dir, planFile))
	if err != nil {
		return nil, fmt.Errorf("replan: no installed plan at %s: %w", filepath.Join(dir, planFile), err)
	}
	installed, err := plan.Parse(installedRaw)
	if err != nil {
		return nil, fmt.Errorf("replan: installed plan is corrupt: %w", err)
	}

	st, err := store.Open(dir, installed, installedRaw, false)
	if err != nil {
		return nil, err
	}

	diff := plan.Diff(installed, revised)
	doneIDs, err := completedIDs(dir)
	if err != nil {
		return nil, err
	}
	sort.Strings(doneIDs)
	discarded := diff.AgainstDone(doneIDs)

	// Kept is the set of surviving nodes whose completion still means what it
	// meant before. Diff already orders its changes by id, so this stays stable.
	kept := make([]string, 0, len(diff.Changes))
	for _, c := range diff.Changes {
		if c.KeepsCompletion {
			kept = append(kept, c.ID)
		}
	}

	if len(discarded) > 0 && !force {
		return nil, fmt.Errorf("refusing to apply: %d verified node(s) would be discarded (%s); pass force=true if that is intended",
			len(discarded), strings.Join(discarded, ", "))
	}

	// The apply cannot simply re-run `dagrun plan`: store.Open refuses a changed
	// plan hash precisely so that a run is never silently reinterpreted under a
	// new plan. Carrying progress forward is the whole point of replanning, so
	// the state is rewritten deliberately: surviving nodes keep their record,
	// invalidated and removed nodes are reset, and new nodes start pending.
	keep := make(map[string]bool, len(kept))
	for _, id := range kept {
		keep[id] = true
	}
	sum := sha256.Sum256(rawPlanBytes)
	hash := hex.EncodeToString(sum[:])

	if err := st.With(func(s *store.State) error {
		next := make(map[string]*store.NodeState, len(revised.Nodes))
		for _, n := range revised.Nodes {
			if n == nil {
				continue
			}
			if prev, ok := s.Nodes[n.ID]; ok && keep[n.ID] {
				next[n.ID] = prev
				continue
			}
			next[n.ID] = &store.NodeState{Status: plan.StatusPending}
		}
		s.Nodes = next
		s.Dynamic = map[string]*plan.Node{}
		s.Expanded = map[string]bool{}
		s.PlanHash = hash
		s.Run = revised.Run
		return nil
	}); err != nil {
		return nil, err
	}

	// Write the plan AFTER the state. A crash between the two leaves a state
	// whose hash does not match run.yaml, which the next Open refuses with
	// "plan changed" — a refusal, never a silent reinterpretation.
	if err := os.WriteFile(filepath.Join(dir, planFile), rawPlanBytes, 0o644); err != nil {
		return nil, fmt.Errorf("state was updated but the plan could not be written: %w", err)
	}

	return &Result{
		Changes:   diff.Changes,
		Kept:      kept,
		Discarded: discarded,
		Blocking:  diff.Blocking,
	}, nil
}

// completedIDs returns the ids the run has actually verified.
//
// It reads state.json directly rather than calling Store.Snapshot: Snapshot
// goes through the store's write path, which bumps UpdatedAt and rewrites the
// document. A refused apply must leave the run byte-for-byte untouched, and a
// "read" that mutates cannot be part of deciding whether to refuse.
//
// Only nodes whose status is exactly "done" count. A node marked done with a
// broken contract is not work worth protecting, and treating it as such would
// let a bad plan revision block a good one.
func completedIDs(dir string) ([]string, error) {
	raw, err := os.ReadFile(filepath.Join(dir, "state.json"))
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	var st store.State
	if err := json.Unmarshal(raw, &st); err != nil {
		return nil, fmt.Errorf("replan: corrupt state at %s: %w", filepath.Join(dir, "state.json"), err)
	}
	// A state written by a newer binary may carry node fields this build does
	// not understand. Refusing here mirrors store.Open rather than guessing.
	if st.Version > store.StateVersion {
		return nil, fmt.Errorf("replan: state is schema version %d, this binary supports %d",
			st.Version, store.StateVersion)
	}
	ids := make([]string, 0, len(st.Nodes))
	for id, ns := range st.Nodes {
		if ns != nil && ns.Status == plan.StatusDone {
			ids = append(ids, id)
		}
	}
	return ids, nil
}
