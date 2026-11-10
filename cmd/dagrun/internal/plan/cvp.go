package plan

import (
	"bufio"
	"bytes"
	"strings"
)

// CVP awareness: answer "what should I do next?" in terms of the checkpoint
// (the CVP gate) rather than the tree.
//
// A checkpoint is closed by one node: the CVP gate. By default that is the last
// GATE node in topological order. A plan may name it explicitly with a
// top-level `cvp_gate: <node id>` key; that key is read from the plan *text*
// (see CVPGateFromYAML / ResolveCVPGate) rather than from a Plan field, because
// a single optional string does not justify widening the plan schema. The plan
// file stays the source of truth.
//
// Direction convention: edges point from a node to the nodes it depends on
// (Node.Deps). "Ancestors of X" therefore means "the work X depends on", and
// the gate's ancestors are exactly the nodes that must finish before the
// checkpoint closes.

// CVPGate returns the id of the node that closes the checkpoint: the last GATE
// node in topological order. It returns "" when the plan declares no GATE node.
//
// An explicit `cvp_gate:` key in the plan file overrides this; callers holding
// the plan text should use ResolveCVPGate instead.
func CVPGate(p *Plan) string {
	if p == nil {
		return ""
	}
	gate := ""
	for _, id := range p.Topo() {
		if n := p.ByID(id); n != nil && n.IsGate() {
			gate = id
		}
	}
	return gate
}

// CVPGateFromYAML scans plan text for a top-level `cvp_gate: <id>` key and
// returns the value. ok is false when the key is absent or empty. This is a
// deliberate raw scan, not a struct field: the key is optional, single-valued,
// and unknown YAML keys are already tolerated by Parse.
func CVPGateFromYAML(raw []byte) (string, bool) {
	sc := bufio.NewScanner(bytes.NewReader(raw))
	sc.Buffer(make([]byte, 0, 64*1024), 1<<20)
	for sc.Scan() {
		line := strings.TrimRight(sc.Text(), " \t\r")
		if !strings.HasPrefix(line, "cvp_gate:") {
			continue
		}
		v := strings.TrimSpace(strings.TrimPrefix(line, "cvp_gate:"))
		if i := strings.Index(v, " #"); i >= 0 {
			v = strings.TrimSpace(v[:i])
		}
		v = strings.Trim(v, `"'`)
		if v == "" {
			return "", false
		}
		return v, true
	}
	return "", false
}

// ResolveCVPGate returns the effective CVP gate: an explicit `cvp_gate:` key in
// raw wins, otherwise the last GATE node in topological order. raw may be nil.
func ResolveCVPGate(p *Plan, raw []byte) string {
	if len(raw) > 0 {
		if id, ok := CVPGateFromYAML(raw); ok && p != nil {
			// Only honour it when it names a node that exists; a typo must not
			// silently retarget the checkpoint.
			if p.ByID(id) != nil {
				return id
			}
		}
	}
	return CVPGate(p)
}

// DistanceTo returns the fewest dependency hops from `from` to `target`,
// following Node.Deps (from -> what from depends on). It returns 0 when
// from == target, and -1 when target is unreachable or either id is unknown.
func DistanceTo(p *Plan, from, target string) int {
	if p == nil || from == "" || target == "" {
		return -1
	}
	idx := p.Index()
	if idx[from] == nil || idx[target] == nil {
		return -1
	}
	if from == target {
		return 0
	}
	dist := map[string]int{from: 0}
	queue := []string{from}
	for len(queue) > 0 {
		cur := queue[0]
		queue = queue[1:]
		n := idx[cur]
		if n == nil {
			continue
		}
		for _, d := range n.Deps {
			if _, seen := dist[d]; seen {
				continue
			}
			if idx[d] == nil {
				continue
			}
			dist[d] = dist[cur] + 1
			if d == target {
				return dist[d]
			}
			queue = append(queue, d)
		}
	}
	return -1
}

// OnPathTo returns every transitive ancestor of target (everything target
// depends on, directly or indirectly). target itself is not included.
func OnPathTo(p *Plan, target string) map[string]bool {
	out := map[string]bool{}
	if p == nil || target == "" {
		return out
	}
	idx := p.Index()
	if idx[target] == nil {
		return out
	}
	stack := []string{target}
	for len(stack) > 0 {
		cur := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		n := idx[cur]
		if n == nil {
			continue
		}
		for _, d := range n.Deps {
			if out[d] || idx[d] == nil {
				continue
			}
			out[d] = true
			stack = append(stack, d)
		}
	}
	return out
}

// CVPDistance returns the hop count from gate down to a node (how far the node
// sits from the checkpoint along dependency edges) and whether the node is on
// the checkpoint's critical work set at all. Unrelated or downstream nodes
// report -1/false.
//
// Distance and MarginalScore both exist on purpose, and they answer different
// questions. Distance is structural: how many hops away is this node? That is
// the right question for "what is blocking the checkpoint", and it is the
// tiebreak when two nodes unlock the same amount of work. MarginalScore is
// economic: how much remaining work does finishing this node release, per
// minute it costs? That is the right question for "which ready node do I run
// next", because two nodes at the same distance can differ by hours of
// downstream work and distance cannot see that difference.
func CVPDistance(p *Plan, gate, node string) (int, bool) {
	if gate == "" || node == "" {
		return -1, false
	}
	if !OnPathTo(p, gate)[node] {
		return -1, false
	}
	return DistanceTo(p, gate, node), true
}

// CVPOrderKey is the sort key for "what should I do next?".
type CVPOrderKey struct {
	// ID is the node id, the final tiebreak.
	ID string
	// Marginal is the node's marginal progress score.
	Marginal float64
	// OnPath reports whether the node is on the checkpoint's work set.
	OnPath bool
	// Distance is the hop count from the gate down to the node.
	Distance int
}

// LessCVPOrderKey reports whether key a sorts before key b.
//
// The order is deliberate:
//
//  1. higher marginal progress first, because it is the only key that
//     measures how much of the remaining critical path a node releases
//  2. nodes on the checkpoint's work set, so checkpoint work stays ahead of
//     side work
//  3. fewer hops from the gate, the distance ordering from before the
//     marginal score existed
//  4. the WBS id, so the order is total and reproducible
func LessCVPOrderKey(a, b CVPOrderKey) bool {
	switch {
	case a.Marginal != b.Marginal:
		return a.Marginal > b.Marginal
	case a.OnPath != b.OnPath:
		return a.OnPath
	case a.OnPath && a.Distance != b.Distance:
		return a.Distance < b.Distance
	default:
		return Less(a.ID, b.ID)
	}
}

// MarginalScore is the estimated reduction in remaining critical-path work
// per estimated minute, [0,1]. A node that sits on the critical path and
// unblocks many minutes of downstream work scores high; a leaf sibling off
// the path scores ~0.
//
// The score is relative to the plan: the best marginal opportunity in the
// plan scores 1.0 and everything else is scaled against it. That makes it a
// ranking signal, which is what an ordering needs, rather than an absolute
// claim about minutes.
//
// A node that reaches nothing on the checkpoint's work set scores exactly 0:
// no amount of work it does can move the checkpoint forward.
//
// It uses the plan's default checkpoint (the last GATE node in topological
// order). A caller that resolved the checkpoint itself, for example from an
// explicit `cvp_gate:` key, must use MarginalScoresFor instead so the score
// and the ordering talk about the same checkpoint.
func MarginalScore(p *Plan, nodeID string) float64 {
	return MarginalScores(p)[nodeID]
}

// MarginalScores returns the marginal score of every node in the plan, using
// the plan's default checkpoint (the last GATE node in topological order).
func MarginalScores(p *Plan) map[string]float64 {
	return MarginalScoresFor(p, CVPGate(p))
}

// MarginalScoresFor returns the marginal score of every node in the plan for
// a specific checkpoint. Callers that resolve the gate themselves (the CLI
// honours an explicit `cvp_gate:` key) must use this, so the scoring and the
// ordering agree on which checkpoint they are talking about.
func MarginalScoresFor(p *Plan, gate string) map[string]float64 {
	out := map[string]float64{}
	if p == nil {
		return out
	}
	ratios := marginalRatios(p, gate)
	if len(ratios) == 0 {
		return out
	}
	best := 0.0
	for _, r := range ratios {
		if r > best {
			best = r
		}
	}
	if best <= 0 {
		return out
	}
	for id, r := range ratios {
		score := r / best
		if score > 1 {
			score = 1
		}
		if score < 0 {
			score = 0
		}
		out[id] = score
	}
	return out
}

// marginalRatios returns, per node, the minutes of checkpoint work it
// unlocks divided by the minutes it costs to run. The ratio is the raw
// marginal value: the score is this number scaled against the best one in
// the plan.
//
// Unlocked work is counted over the checkpoint's critical work set (the
// checkpoint plus everything it transitively depends on). A node unlocks the
// part of that set it gates: everything downstream of it on the way to the
// checkpoint, the checkpoint itself included.
func marginalRatios(p *Plan, gate string) map[string]float64 {
	ratios := map[string]float64{}
	if p == nil || gate == "" {
		return ratios
	}
	if p.ByID(gate) == nil {
		return ratios
	}
	critical := OnPathTo(p, gate)
	critical[gate] = true

	unlocked := map[string]float64{}
	for _, n := range p.Sorted() {
		if !critical[n.ID] {
			continue
		}
		mins := p.estimateMinutes(n)
		if mins <= 0 {
			continue
		}
		// Everything that depends on this node inherits this node's minutes:
		// finishing an ancestor is part of finishing a dependent, so the
		// ancestor releases that work.
		for anc := range OnPathTo(p, n.ID) {
			unlocked[anc] += mins
		}
	}
	for _, n := range p.Sorted() {
		own := p.estimateMinutes(n)
		if own <= 0 {
			continue
		}
		if u := unlocked[n.ID]; u > 0 {
			ratios[n.ID] = u / own
		}
	}
	return ratios
}

// estimateMinutes returns a node's estimated minutes. A node with no estimate
// inherits the plan default, and an unparsable estimate falls back to the
// same 10m the rest of the package uses, so the divisor is never zero.
func (p *Plan) estimateMinutes(n *Node) float64 {
	if n == nil {
		return 0
	}
	raw := n.Estimate
	if raw == "" {
		raw = p.Defaults.Estimate
	}
	d, err := ParseEstimate(raw)
	if err != nil || d <= 0 {
		return defaultEstimateMinutes
	}
	return d.Minutes()
}

// defaultEstimateMinutes is the fallback estimate used when a node declares
// none and the plan declares no default either.
const defaultEstimateMinutes = 10.0
