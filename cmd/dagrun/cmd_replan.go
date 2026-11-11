package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/replan"
)

// cmdReplan compares an installed run against a revised plan and says what the
// revision would cost.
//
// The one behaviour that matters: it refuses to discard verified work. A plan
// revision is cheap to make and expensive to get wrong, and the failure mode —
// a node that was "done" becoming pending with no explanation — looks
// indistinguishable from lost work. So the default is a report, and applying it
// requires --apply, which requires the discard to be either empty or forced.
//
// The mutation itself lives in internal/replan so an MCP client can reach the
// same guarantees; this command only reports and then delegates.
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

	res, err := replan.Apply(dir, revised, raw, *force)
	if err != nil {
		return err
	}
	fmt.Printf("applied %s: %d node(s) kept, %d reset\n", pos[0], len(res.Kept), len(res.Discarded))
	return nil
}
