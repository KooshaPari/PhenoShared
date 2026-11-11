package plan

import (
	"fmt"
	"sort"
	"strings"
)

// Replanning: answer "what did this plan revision change?" without losing
// track of work the run already verified.
//
// A plan is revised mid-run more often than anyone admits: a node's contract
// is tightened, a title is fixed, a branch is dropped. The danger is not the
// edit itself, it is the silent consequence: a node that was verified under
// the old contract is still marked done under the new one, and the run
// claims a piece of evidence it never produced.
//
// This file is deliberately a pure function over two plans. It does not
// import internal/store and never reads run state, because the question it
// answers ("is this node's completion still valid?") must be answerable
// before the store is consulted, and because a diff that could see the run
// would quietly become a policy decision instead of a report.
//
// The division of labour is:
//
//	Diff          structural: what changed between the two plans
//	AgainstDone   run-aware: which already-verified results the new plan
//	              would drop
//
// The caller owns the refusal. Diff tells it what is at stake; AgainstDone
// tells it what has already been earned; the caller decides whether to
// re-verify, to keep the old result, or to stop and ask.

// ChangeKind classifies what happened to one node between two plans.
type ChangeKind string

const (
	// ChangeAdded is a node that exists only in the new plan. It has no
	// history, so it never keeps a completion and never blocks.
	ChangeAdded ChangeKind = "added"
	// ChangeRemoved is a node that existed in the old plan and is gone from
	// the new one.
	ChangeRemoved ChangeKind = "removed"
	// ChangeContractChanged is a node whose verification contract changed:
	// its artifacts, check, kind, or role. Its old completion no longer
	// proves anything, so the node must be verified again.
	ChangeContractChanged ChangeKind = "contract_changed"
	// ChangeDepsChanged is a node whose dependency set changed. The work
	// itself is the same, but it now runs under different preconditions, so
	// a completion earned before the edit is stale.
	ChangeDepsChanged ChangeKind = "deps_changed"
	// ChangeRenamedTitle is a node whose title changed and nothing else.
	// Cosmetic: the completion still stands.
	ChangeRenamedTitle ChangeKind = "renamed_title"
	// ChangeUnchanged is a node that is identical in both plans.
	ChangeUnchanged ChangeKind = "unchanged"
)

// NodeChange is what happened to one node.
type NodeChange struct {
	// ID is the node id, shared by both plans.
	ID string `json:"id"`
	// Kind classifies the change.
	Kind ChangeKind `json:"kind"`
	// Detail explains the change in one human-readable clause.
	Detail string `json:"detail,omitempty"`
	// KeepsCompletion says whether a completion already earned by this node
	// still proves the node is done under the new plan.
	KeepsCompletion bool `json:"keeps_completion"`
}

// ReplanDiff is the result of comparing two plans.
type ReplanDiff struct {
	// Changes lists every node in either plan, ordered by id.
	Changes []NodeChange `json:"changes"`
	// Safe reports that no surviving node lost its contract: nothing that
	// was verified has to be verified again because the plan changed
	// underneath it.
	//
	// Safe does NOT mean the new plan keeps every verified result. A node
	// that disappeared entirely cannot be judged here, because Diff cannot
	// see which nodes were done. Check AgainstDone before adopting a
	// replan; that is the call that turns this report into a refusal.
	Safe bool `json:"safe"`
	// Blocking lists the ids of nodes whose completion was invalidated and
	// which therefore need to be verified again.
	Blocking []string `json:"blocking,omitempty"`
}

// Diff compares two plans node by node and reports what a replan would do to
// the work that is already done.
//
// The rules it encodes:
//
//	same contract, same deps   completion stands (even if the title changed)
//	contract changed            completion is void, node is blocking
//	dependency set changed      completion is void, node is blocking
//	node removed                completion is void, node is NOT blocking here
//	node added                  nothing to keep, never blocking
//
// The removal rule is the subtle one. Whether dropping a node is safe
// depends on whether that node had been verified, and Diff cannot know that:
// it sees plans, not runs. So a removal is reported as a node change with
// KeepsCompletion false and is deliberately left out of Blocking. The caller
// decides, using AgainstDone with the verified set, whether the removal
// actually costs anything.
func Diff(old, new *Plan) ReplanDiff {
	oldIdx := planIndex(old)
	newIdx := planIndex(new)

	ids := make([]string, 0, len(oldIdx)+len(newIdx))
	seen := map[string]bool{}
	for id := range oldIdx {
		if !seen[id] {
			seen[id] = true
			ids = append(ids, id)
		}
	}
	for id := range newIdx {
		if !seen[id] {
			seen[id] = true
			ids = append(ids, id)
		}
	}
	// Stable ordering by id: the same pair of plans must always produce the
	// same report, whatever order the nodes were written in.
	sort.Slice(ids, func(i, j int) bool { return Less(ids[i], ids[j]) })

	d := ReplanDiff{Safe: true}
	for _, id := range ids {
		o, inOld := oldIdx[id]
		n, inNew := newIdx[id]
		switch {
		case inOld && !inNew:
			d.Changes = append(d.Changes, NodeChange{
				ID:   id,
				Kind: ChangeRemoved,
				// The completion is void: there is no node left to be done.
				// Whether that costs anything is the caller's call, see the
				// rule table above.
				Detail:          fmt.Sprintf("removed from the new plan (was kind %q)", o.Kind),
				KeepsCompletion: false,
			})
		case !inOld && inNew:
			d.Changes = append(d.Changes, NodeChange{
				ID:              id,
				Kind:            ChangeAdded,
				Detail:          fmt.Sprintf("added to the new plan (kind %q)", n.Kind),
				KeepsCompletion: false,
			})
		default:
			d.Changes = append(d.Changes, compareNode(o, n))
		}
	}

	for _, c := range d.Changes {
		if c.KeepsCompletion {
			continue
		}
		switch c.Kind {
		case ChangeContractChanged, ChangeDepsChanged:
			d.Blocking = append(d.Blocking, c.ID)
			d.Safe = false
		}
	}
	return d
}

// AgainstDone returns the verified node ids the new plan would silently drop.
//
// This is where "refuse to silently discard verified work" becomes
// enforceable. The caller passes the set of node ids the run has already
// verified; a non-empty result means the replan cannot be applied as-is,
// because something the run already proved would have to be done again.
//
// A verified id that is missing from the diff entirely is reported too: it
// was verified under the old plan, and the new plan does not contain it at
// all.
//
// The result is ordered by id and free of duplicates, so it can be printed
// or compared directly.
func (d ReplanDiff) AgainstDone(doneIDs []string) []string {
	keeps := make(map[string]bool, len(d.Changes))
	for _, c := range d.Changes {
		keeps[c.ID] = c.KeepsCompletion
	}
	var out []string
	seen := map[string]bool{}
	for _, id := range doneIDs {
		if id == "" || seen[id] {
			continue
		}
		seen[id] = true
		if !keeps[id] {
			out = append(out, id)
		}
	}
	sort.Slice(out, func(i, j int) bool { return Less(out[i], out[j]) })
	return out
}

// compareNode classifies the difference between the two versions of one node.
func compareNode(old, updated *Node) NodeChange {
	c := NodeChange{ID: old.ID}
	oc, nc := contractOf(old), contractOf(updated)
	if oc != nc {
		c.Kind = ChangeContractChanged
		c.Detail = contractDetail(oc, nc)
		c.KeepsCompletion = false
		return c
	}
	if canonicalDeps(old.Deps) != canonicalDeps(updated.Deps) {
		c.Kind = ChangeDepsChanged
		c.Detail = depsDetail(old.Deps, updated.Deps)
		c.KeepsCompletion = false
		return c
	}
	if old.Title != updated.Title {
		// A title is how the work is described, not what it must produce.
		// Renaming a node does not invalidate what it already produced.
		c.Kind = ChangeRenamedTitle
		c.Detail = fmt.Sprintf("title %q -> %q", old.Title, updated.Title)
		c.KeepsCompletion = true
		return c
	}
	c.Kind = ChangeUnchanged
	c.KeepsCompletion = true
	return c
}

// nodeContract is the part of a node that decides what "done" means for it:
// the artifacts it must produce, the check it must pass, and the kind and
// role that give those artifacts their meaning. Two nodes with the same
// contract are interchangeable as far as verification goes, so a completion
// earned by one is still evidence for the other.
//
// Everything else a node carries (prompt text, harness, estimate, timeout)
// describes how the work is carried out, not what it must leave behind, so
// none of it can invalidate a completion.
type nodeContract struct {
	kind      string
	role      string
	check     string
	artifacts string
}

func contractOf(n *Node) nodeContract {
	return nodeContract{
		kind:      n.Kind,
		role:      n.Role,
		check:     n.Check,
		artifacts: canonicalArtifacts(n.Artifacts),
	}
}

// canonicalArtifacts renders an artifact list as one comparable string.
// Artifact order and must_contain order are presentation rather than
// predicate: reordering them does not change what the node must produce, so
// it must not be reported as a contract change.
func canonicalArtifacts(arts []Artifact) string {
	parts := make([]string, 0, len(arts))
	for _, a := range arts {
		must := append([]string(nil), a.MustContain...)
		sort.Strings(must)
		parts = append(parts, fmt.Sprintf("%s|%d|%s|%s|%d|%t",
			a.Path, a.MinBytes, strings.Join(must, ","), a.MustMatch, a.MinCount, a.AllowEmpty))
	}
	sort.Strings(parts)
	return strings.Join(parts, ";")
}

// canonicalDeps renders a dependency list as one comparable string. The set
// of dependencies is what matters, not the order they are written in.
func canonicalDeps(deps []string) string {
	d := append([]string(nil), deps...)
	sort.Strings(d)
	return strings.Join(d, ",")
}

// contractDetail names the contract fields that differ.
func contractDetail(old, new nodeContract) string {
	var parts []string
	if old.kind != new.kind {
		parts = append(parts, fmt.Sprintf("kind %q -> %q", old.kind, new.kind))
	}
	if old.role != new.role {
		parts = append(parts, fmt.Sprintf("role %q -> %q", old.role, new.role))
	}
	if old.check != new.check {
		parts = append(parts, fmt.Sprintf("check %q -> %q", old.check, new.check))
	}
	if old.artifacts != new.artifacts {
		parts = append(parts, "artifacts changed")
	}
	return strings.Join(parts, "; ")
}

// depsDetail names the dependencies that were added and removed.
func depsDetail(old, new []string) string {
	oldSet := map[string]bool{}
	for _, d := range old {
		oldSet[d] = true
	}
	newSet := map[string]bool{}
	for _, d := range new {
		newSet[d] = true
	}
	var added, removed []string
	for d := range newSet {
		if !oldSet[d] {
			added = append(added, d)
		}
	}
	for d := range oldSet {
		if !newSet[d] {
			removed = append(removed, d)
		}
	}
	sort.Strings(added)
	sort.Strings(removed)
	var parts []string
	if len(added) > 0 {
		parts = append(parts, "added "+strings.Join(added, ","))
	}
	if len(removed) > 0 {
		parts = append(parts, "removed "+strings.Join(removed, ","))
	}
	return strings.Join(parts, "; ")
}

// planIndex maps node id to node for a plan, tolerating a nil plan.
func planIndex(p *Plan) map[string]*Node {
	if p == nil {
		return map[string]*Node{}
	}
	return p.Index()
}
