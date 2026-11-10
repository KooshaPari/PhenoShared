package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// cmdReplan compares an installed run against a revised plan and says what the
// revision would cost.
//
// The one behaviour that matters: it refuses to discard verified work. A plan
// revision is cheap to make and expensive to get wrong, and the failure mode —
// a node that was "done" becoming pending with no explanation — looks
// indistinguishable from lost work. So the default is a report, and applying it
// requires --apply, which requires the discard to be either empty or forced.
func cmdReplan(args []string) error {
	var dir string
	flags, pos := splitArgs(args)
	fs := flagSet("replan", &dir, nil)
	apply := fs.Bool("apply", false, "install the revised plan once it is accepted")
	force := fs.Bool("force", false, "apply even though verified work would be discarded")
	if err := fs.Parse(flags); err != nil {
		return err
	}
	if len(pos) == 0 {
		return fmt.Errorf("usage: dagrun replan PLAN.yaml [--apply] [--force]")
	}

	_, st, _, err := openRun(dir)
	if err != nil {
		return err
	}
	installed := st.Plan()

	raw, err := os.ReadFile(pos[0])
	if err != nil {
		return err
	}
	revised, err := plan.Parse(raw)
	if err != nil {
		return fmt.Errorf("%s: %w", pos[0], err)
	}
	if issues := revised.Validate(); len(issues) > 0 {
		return fmt.Errorf("%s is not a valid plan: %v", pos[0], issues)
	}

	diff := plan.Diff(installed, revised)
	snap, err := st.Snapshot()
	if err != nil {
		return err
	}

	// Only nodes that actually verified count as done. A node marked done with a
	// broken contract is not work worth protecting, and treating it as such
	// would let a bad plan revision block a good one.
	doneIDs := make([]string, 0, len(snap.Nodes))
	for id, ns := range snap.Nodes {
		if ns != nil && ns.Status == plan.StatusDone {
			doneIDs = append(doneIDs, id)
		}
	}
	sort.Strings(doneIDs)
	discard := diff.AgainstDone(doneIDs)

	fmt.Printf("run %s -> %s\n", installed.Run, revised.Run)
	if len(diff.Changes) == 0 {
		fmt.Println("no structural change")
	} else {
		for _, c := range diff.Changes {
			marker := " "
			switch {
			case c.Kind == "unchanged":
				continue
			case c.KeepsCompletion:
				marker = "="
			default:
				marker = "!"
			}
			fmt.Printf("  %s %-10s %-18s %s\n", marker, c.ID, c.Kind, c.Detail)
		}
	}
	if len(discard) > 0 {
		fmt.Printf("\nverified work this revision would discard: %s\n", strings.Join(discard, ", "))
	}
	if len(diff.Blocking) > 0 {
		fmt.Printf("blocking change(s): %s\n", strings.Join(diff.Blocking, ", "))
	}

	if !*apply {
		fmt.Print("\nreport only. pass --apply to install the revised plan.\n")
		return nil
	}
	if len(discard) > 0 && !*force {
		return fmt.Errorf("refusing to apply: %d verified node(s) would be discarded (%s); pass --force if that is intended",
			len(discard), strings.Join(discard, ", "))
	}

	// The apply cannot simply re-run `dagrun plan`: store.Open refuses a changed
	// plan hash precisely so that a run is never silently reinterpreted under a
	// new plan. Carrying progress forward is the whole point of replanning, so
	// the state is rewritten deliberately: surviving nodes keep their record,
	// invalidated and removed nodes are reset, and new nodes start pending.
	keep := map[string]bool{}
	for _, c := range diff.Changes {
		if c.KeepsCompletion {
			keep[c.ID] = true
		}
	}
	sum := sha256.Sum256(raw)
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
		return err
	}

	// Write the plan AFTER the state. A crash between the two leaves a state
	// whose hash does not match run.yaml, which the next Open refuses with
	// "plan changed" — a refusal, never a silent reinterpretation.
	if err := os.WriteFile(filepath.Join(dir, "run.yaml"), raw, 0o644); err != nil {
		return fmt.Errorf("state was updated but the plan could not be written: %w", err)
	}
	fmt.Printf("applied %s: %d node(s) kept, %d reset\n", pos[0], len(keep), len(discard))
	return nil
}
