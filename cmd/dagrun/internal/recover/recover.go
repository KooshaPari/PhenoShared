// Package recover inspects and repairs a run directory whose nodes are stuck in
// a running state.
//
// The distinction that matters: an EXPIRED lease is already safe to reap, and
// `dagrun run` and `dagrun next` do it automatically. A lease still in the
// future whose worker is gone is the dangerous case, because from the store's
// point of view the work may still be happening. Reclaiming that is only ever
// allowed with --force, and it is never silent.
//
// Report is read-only by construction: it parses run.yaml and state.json
// directly and never opens the store, because store.Open creates directories
// and an inspection must not change the thing it is describing. Reclaim is the
// mutation, and it goes through the store so it takes the same lock a worker
// does.
//
// Lifting this out of package main matters because a wedged run is exactly the
// situation an MCP client or an external supervisor has to diagnose, and code
// that lives in a CLI command cannot be reused by them.
package recover

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// Stuck is one node found in a running state, with the evidence that says
// whether reclaiming it is safe.
type Stuck struct {
	ID       string    `json:"id"`
	Owner    string    `json:"owner,omitempty"`
	Lease    time.Time `json:"lease_until,omitempty"`
	Expired  bool      `json:"expired"`
	Attempts int       `json:"attempts,omitempty"`
	Reason   string    `json:"reason"`
}

// The reasons a running node is reported. They are the whole point of the
// report: "running" alone does not say whether a worker is alive, so each case
// names the evidence instead.
const (
	reasonLiveLease      = "lease is live; a worker may still be running this node"
	reasonNoOwnerNoLease = "running with no owner and no lease; whoever took it never recorded itself"
	reasonNoOwner        = "running with a lease but no owner"
	reasonExpired        = "lease expired; the owner is gone"
)

// reclaimError is what LastError records on a node that was forced back to
// pending, so the next reader can tell a repair from a fresh attempt.
const reclaimError = "reclaimed by dagrun recover --force"

// Report lists every node in a running state. It never mutates.
//
// The returned ids are ordered by node id, so two runs over the same directory
// print the same report.
func Report(dir string) (run string, stuck []Stuck, err error) {
	p, st, err := load(dir)
	if err != nil {
		return "", nil, err
	}
	now := time.Now()
	for _, id := range knownIDs(p, st) {
		ns := st.Nodes[id]
		if ns == nil || ns.Status != plan.StatusRunning {
			continue
		}
		expired := !ns.LeaseUntil.After(now)
		reason := reasonLiveLease
		switch {
		case ns.Owner == "" && ns.LeaseUntil.IsZero():
			reason = reasonNoOwnerNoLease
		case ns.Owner == "":
			reason = reasonNoOwner
		case expired:
			reason = reasonExpired
		}
		stuck = append(stuck, Stuck{
			ID:       id,
			Owner:    ns.Owner,
			Lease:    ns.LeaseUntil,
			Expired:  expired,
			Attempts: ns.Attempts,
			Reason:   reason,
		})
	}
	return p.Run, stuck, nil
}

// Reclaim returns the stuck nodes to pending. An empty ids means every stuck
// node. It returns the ids it actually reclaimed.
//
// Reclaiming does NOT reset the attempt counter. A reclaimed node keeps the
// attempts it already spent, so a crash loop cannot buy itself unlimited
// retries by being recovered over and over.
//
// Any id that is no longer running is skipped, so a reclaim racing a worker is
// safe, and a second Reclaim on the same directory returns nothing new.
func Reclaim(dir string, ids []string) ([]string, error) {
	p, raw, err := loadPlan(dir)
	if err != nil {
		return nil, err
	}
	st, err := store.Open(dir, p, raw, false)
	if err != nil {
		return nil, err
	}

	want := make(map[string]bool, len(ids))
	for _, id := range ids {
		if id != "" {
			want[id] = true
		}
	}

	var reclaimed []string
	err = st.With(func(state *store.State) error {
		keys := make([]string, 0, len(state.Nodes))
		for id := range state.Nodes {
			keys = append(keys, id)
		}
		sort.Strings(keys)
		for _, id := range keys {
			ns := state.Nodes[id]
			if ns == nil || ns.Status != plan.StatusRunning {
				continue
			}
			if len(want) > 0 && !want[id] {
				continue
			}
			ns.Status = plan.StatusPending
			ns.Owner = ""
			ns.LeaseUntil = time.Time{}
			ns.LastError = reclaimError
			reclaimed = append(reclaimed, id)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	sort.Strings(reclaimed)
	return reclaimed, nil
}

// loadPlan reads and parses run.yaml, returning the source bytes because the
// store hashes them to decide whether a run directory still matches its plan.
func loadPlan(dir string) (*plan.Plan, []byte, error) {
	raw, err := os.ReadFile(filepath.Join(dir, "run.yaml"))
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil, fmt.Errorf("no plan installed at %s; run `dagrun plan FILE` first",
				filepath.Join(dir, "run.yaml"))
		}
		return nil, nil, fmt.Errorf("read plan in %s: %w", dir, err)
	}
	p, err := plan.Parse(raw)
	if err != nil {
		return nil, nil, fmt.Errorf("parse plan in %s: %w", dir, err)
	}
	return p, raw, nil
}

// load reads the plan and the state. Unlike a query, a missing state.json is an
// error here: this package exists to report on a run that HAS progress stuck in
// it, and a run with no state has nothing stuck. Reporting "nothing is stuck"
// for a directory that was never started would be an invented answer.
func load(dir string) (*plan.Plan, *store.State, error) {
	p, _, err := loadPlan(dir)
	if err != nil {
		return nil, nil, err
	}
	sraw, err := os.ReadFile(filepath.Join(dir, "state.json"))
	if err != nil {
		return nil, nil, fmt.Errorf("read state in %s: %w", dir, err)
	}
	var st store.State
	if err := json.Unmarshal(sraw, &st); err != nil {
		return nil, nil, fmt.Errorf("parse state.json in %s: %w", dir, err)
	}
	return p, &st, nil
}

// knownIDs is the set of node ids the store considers part of this run: the
// plan's static nodes plus the ones materialised at runtime. A state entry for
// anything else is not a node of this run and is ignored, exactly as the store's
// own node listing does.
func knownIDs(p *plan.Plan, st *store.State) []string {
	seen := make(map[string]bool, len(p.Nodes)+len(st.Dynamic))
	ids := make([]string, 0, len(p.Nodes)+len(st.Dynamic))
	add := func(id string) {
		if id == "" || seen[id] {
			return
		}
		seen[id] = true
		ids = append(ids, id)
	}
	for _, n := range p.Nodes {
		if n != nil {
			add(n.ID)
		}
	}
	dynamic := make([]string, 0, len(st.Dynamic))
	for id, n := range st.Dynamic {
		if n != nil {
			dynamic = append(dynamic, id)
		}
	}
	sort.Strings(dynamic)
	for _, id := range dynamic {
		add(id)
	}
	sort.Strings(ids)
	return ids
}
