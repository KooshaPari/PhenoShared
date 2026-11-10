package main

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"
	"time"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// stuckNode is one node `recover` found in a running state, with the evidence
// that says whether reclaiming it is safe.
type stuckNode struct {
	ID       string    `json:"id"`
	Owner    string    `json:"owner,omitempty"`
	Lease    time.Time `json:"lease_until,omitempty"`
	Expired  bool      `json:"expired"`
	Attempts int       `json:"attempts,omitempty"`
	Reason   string    `json:"reason"`
}

// cmdRecover is the deliberate, opt-in repair for a wedged run directory.
//
// The distinction that matters: an EXPIRED lease is already safe to reap, and
// `dagrun run` and `dagrun next` do it automatically. A lease still in the
// future whose worker is gone is the dangerous case, because from the store's
// point of view the work may still be happening. Reclaiming that is only ever
// allowed with --force, and it is never silent.
//
// Recovering does NOT reset the attempt counter. A reclaimed node keeps the
// attempts it already spent, so a crash loop cannot buy itself unlimited
// retries by being recovered over and over.
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

	p, st, _, err := openRun(dir)
	if err != nil {
		return err
	}
	snap, err := st.Snapshot()
	if err != nil {
		return err
	}

	want := map[string]bool{}
	for _, id := range splitList(*only) {
		want[id] = true
	}

	now := time.Now()
	var found []stuckNode
	for _, n := range st.All(snap) {
		ns := snap.Nodes[n.ID]
		if ns == nil || ns.Status != plan.StatusRunning {
			continue
		}
		if len(want) > 0 && !want[n.ID] {
			continue
		}
		expired := !ns.LeaseUntil.After(now)
		reason := "lease is live; a worker may still be running this node"
		switch {
		case ns.Owner == "" && ns.LeaseUntil.IsZero():
			reason = "running with no owner and no lease; whoever took it never recorded itself"
		case ns.Owner == "":
			reason = "running with a lease but no owner"
		case expired:
			reason = "lease expired; the owner is gone"
		}
		found = append(found, stuckNode{
			ID:       n.ID,
			Owner:    ns.Owner,
			Lease:    ns.LeaseUntil,
			Expired:  expired,
			Attempts: ns.Attempts,
			Reason:   reason,
		})
	}
	sort.Slice(found, func(i, j int) bool { return found[i].ID < found[j].ID })

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
			"run":        p.Run,
			"forced":     *force,
			"candidates": found,
			"recovered":  recovered,
		})
	}

	if len(found) == 0 {
		fmt.Printf("run %s: nothing is stuck\n", p.Run)
		return nil
	}

	fmt.Printf("run %s: %d node(s) in a running state\n", p.Run, len(found))
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

	if err := st.With(func(state *store.State) error {
		for _, id := range ids {
			ns := state.Nodes[id]
			if ns == nil || ns.Status != plan.StatusRunning {
				continue
			}
			ns.Status = plan.StatusPending
			ns.Owner = ""
			ns.LeaseUntil = time.Time{}
			ns.LastError = "reclaimed by dagrun recover --force"
		}
		return nil
	}); err != nil {
		return err
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
