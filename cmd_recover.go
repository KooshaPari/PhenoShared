package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/KooshaPari/dagrun/internal/recover"
)

// cmdRecover is the deliberate, opt-in repair for a wedged run directory.
//
// The logic lives in internal/recover so an MCP client or a supervisor can
// reuse it; this command is only the flag parsing and the human-readable
// rendering of it. See that package for why an expired lease is safe to reap
// and a live lease is not, and for why a reclaim never resets the attempt
// counter.
func cmdRecover(args []string) error {
	var dir string
	var jsonOut bool
	flags, _ := splitArgs(args)
	fs := flagSet("recover", &dir, &jsonOut)
	force := fs.Bool("force", false, "actually reclaim stuck nodes; without this the command only reports")
	only := fs.String("node", "", "comma-separated node ids to limit the repair to")
	if err := fs.Parse(flags); err != nil {
		return err
	}

	run, found, err := recover.Report(dir)
	if err != nil {
		return err
	}

	want := map[string]bool{}
	for _, id := range splitList(*only) {
		want[id] = true
	}
	if len(want) > 0 {
		// nil, not an empty slice: a filtered-out --node set must still encode as
		// JSON null, exactly as the pre-package command did.
		var limited []recover.Stuck
		for _, s := range found {
			if want[s.ID] {
				limited = append(limited, s)
			}
		}
		found = limited
	}

	ids := make([]string, 0, len(found))
	for _, v := range found {
		ids = append(ids, v.ID)
	}

	if jsonOut {
		recovered := []string{}
		if *force {
			recovered = ids
		}
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		return enc.Encode(map[string]any{
			"run":        run,
			"forced":     *force,
			"candidates": found,
			"recovered":  recovered,
		})
	}

	if len(found) == 0 {
		fmt.Printf("run %s: nothing is stuck\n", run)
		return nil
	}

	fmt.Printf("run %s: %d node(s) in a running state\n", run, len(found))
	for _, s := range found {
		lease := "none"
		if !s.Lease.IsZero() {
			lease = s.Lease.Format(time.RFC3339)
		}
		fmt.Printf("  %-10s owner=%-12s lease=%-25s attempts=%d  %s\n",
			s.ID, orNone(s.Owner), lease, s.Attempts, s.Reason)
	}

	if !*force {
		fmt.Print("\nreport only. re-run with --force to reclaim these nodes to pending.\n" +
			"reclaiming keeps the attempt count, so no free retries are granted.\n")
		return nil
	}

	reclaimed, err := recover.Reclaim(dir, ids)
	if err != nil {
		return err
	}
	// In the ordinary case this is every id we reported. If a worker slipped in
	// between the report and the reclaim, the reclaim is the authority: say what
	// actually moved rather than repeating the plan.
	if len(reclaimed) != len(ids) {
		ids = reclaimed
	}
	fmt.Printf("\nreclaimed %d node(s) to pending: %s\n", len(ids), strings.Join(ids, ", "))
	return nil
}

func orNone(s string) string {
	if s == "" {
		return "-"
	}
	return s
}
