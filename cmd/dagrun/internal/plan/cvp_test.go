package plan

import (
	"sort"
	"testing"
)

const chainYAML = `
version: 1
run: chain
nodes:
  - id: "1"
    kind: INTENT
  - id: "2"
    kind: SPEC
    deps: ["1"]
  - id: "3"
    kind: IMPL
    deps: ["2"]
  - id: "4"
    kind: GATE
    deps: ["3"]
`

const diamondYAML = `
version: 1
run: diamond
nodes:
  - id: "1"
    kind: INTENT
  - id: "2"
    kind: SPEC
    deps: ["1"]
  - id: "3"
    kind: RESEARCH
    deps: ["1"]
  - id: "4"
    kind: IMPL
    deps: ["2", "3"]
  - id: "5"
    kind: OTHER
`

func TestCVPDistanceToChain(t *testing.T) {
	p := parsePlan(t, chainYAML)
	cases := []struct {
		from, target string
		want         int
	}{
		{"1", "1", 0},
		{"2", "1", 1},
		{"3", "1", 2},
		{"4", "1", 3},
		{"1", "4", -1}, // edges point at deps, not dependents
		{"4", "4", 0},
		{"1", "nope", -1},
		{"nope", "1", -1},
		{"", "1", -1},
	}
	for _, c := range cases {
		if got := DistanceTo(p, c.from, c.target); got != c.want {
			t.Errorf("DistanceTo(%q,%q) = %d, want %d", c.from, c.target, got, c.want)
		}
	}
}

func TestCVPDistanceToDiamond(t *testing.T) {
	p := parsePlan(t, diamondYAML)
	cases := []struct {
		from, target string
		want         int
	}{
		{"4", "1", 2}, // 4 -> 2 -> 1 (not 3)
		{"4", "2", 1},
		{"4", "3", 1},
		{"2", "1", 1},
		{"5", "1", -1}, // disconnected node
	}
	for _, c := range cases {
		if got := DistanceTo(p, c.from, c.target); got != c.want {
			t.Errorf("DistanceTo(%q,%q) = %d, want %d", c.from, c.target, got, c.want)
		}
	}
}

func TestCVPOnPathToAncestors(t *testing.T) {
	p := parsePlan(t, diamondYAML)
	got := OnPathTo(p, "4")
	want := []string{"1", "2", "3"}
	if len(got) != len(want) {
		t.Fatalf("OnPathTo(4) = %v, want exactly %v", got, want)
	}
	for _, id := range want {
		if !got[id] {
			t.Errorf("OnPathTo(4) missing ancestor %q (got %v)", id, got)
		}
	}
	if got["4"] {
		t.Errorf("OnPathTo(4) must not include the target itself")
	}
	if got["5"] {
		t.Errorf("OnPathTo(4) must not include the disconnected node 5")
	}
	if len(OnPathTo(p, "5")) != 0 {
		t.Errorf("OnPathTo(5) should be empty, got %v", OnPathTo(p, "5"))
	}
	if len(OnPathTo(p, "missing")) != 0 {
		t.Errorf("OnPathTo(missing) should be empty")
	}
}

func TestCVPGatePicksLastGateInTopoOrder(t *testing.T) {
	p := parsePlan(t, `
version: 1
run: two-gates
nodes:
  - id: "1"
    kind: INTENT
  - id: "2"
    kind: GATE
    deps: ["1"]
  - id: "3"
    kind: IMPL
    deps: ["2"]
  - id: "4"
    kind: GATE
    deps: ["3"]
  - id: "9"
    kind: DOC
`)
	if got := CVPGate(p); got != "4" {
		t.Fatalf("CVPGate = %q, want %q (last GATE in topo order)", got, "4")
	}
}

func TestCVPGateNoneDeclared(t *testing.T) {
	p := parsePlan(t, diamondYAML)
	if got := CVPGate(p); got != "" {
		t.Fatalf("CVPGate on a plan with no GATE = %q, want empty", got)
	}
	if _, ok := CVPGateFromYAML([]byte(diamondYAML)); ok {
		t.Fatalf("CVPGateFromYAML found a cvp_gate key that is not there")
	}
}

func TestCVPGateExplicitKeyOverrides(t *testing.T) {
	// The gate id here is 2, which topologically precedes gate 4, so only the
	// explicit key can produce it.
	raw := []byte(`
version: 1
run: explicit
cvp_gate: "2"
nodes:
  - id: "1"
    kind: INTENT
  - id: "2"
    kind: GATE
    deps: ["1"]
  - id: "3"
    kind: IMPL
    deps: ["2"]
  - id: "4"
    kind: GATE
    deps: ["3"]
`)
	p := parsePlan(t, string(raw))

	if got, ok := CVPGateFromYAML(raw); !ok || got != "2" {
		t.Fatalf("CVPGateFromYAML = (%q,%v), want (\"2\",true)", got, ok)
	}
	if got := ResolveCVPGate(p, raw); got != "2" {
		t.Fatalf("ResolveCVPGate = %q, want explicit key %q", got, "2")
	}
	// Without the plan text, the topo default wins.
	if got := ResolveCVPGate(p, nil); got != "4" {
		t.Fatalf("ResolveCVPGate(nil) = %q, want topo default %q", got, "4")
	}
}

func TestCVPGateFromYAMLForms(t *testing.T) {
	cases := []struct {
		name string
		in   string
		want string
		ok   bool
	}{
		{"plain", "run: x\ncvp_gate: \"3.2\"\nnodes: []\n", "3.2", true},
		{"unquoted", "cvp_gate: 3.2\n", "3.2", true},
		{"single quotes", "cvp_gate: '3.2'\n", "3.2", true},
		{"trailing comment", "cvp_gate: \"3.2\" # the checkpoint\n", "3.2", true},
		{"trailing spaces", "cvp_gate: 3.2   \n", "3.2", true},
		{"empty value", "cvp_gate:\n", "", false},
		{"absent", "run: x\n", "", false},
		{"nested is not top level", "  cvp_gate: 3.2\n", "", false},
	}
	for _, c := range cases {
		got, ok := CVPGateFromYAML([]byte(c.in))
		if got != c.want || ok != c.ok {
			t.Errorf("%s: CVPGateFromYAML = (%q,%v), want (%q,%v)", c.name, got, ok, c.want, c.ok)
		}
	}
}

func TestCVPGateExplicitKeyUnknownNodeIgnored(t *testing.T) {
	// A typo must not silently retarget the checkpoint.
	raw := []byte(`
version: 1
run: chain
cvp_gate: "nope"
nodes:
  - id: "1"
    kind: INTENT
  - id: "2"
    kind: SPEC
    deps: ["1"]
  - id: "4"
    kind: GATE
    deps: ["2"]
`)
	p := parsePlan(t, string(raw))
	if got, ok := CVPGateFromYAML(raw); !ok || got != "nope" {
		t.Fatalf("CVPGateFromYAML = %q, want the raw value %q", got, "nope")
	}
	if got := ResolveCVPGate(p, raw); got != "4" {
		t.Fatalf("ResolveCVPGate with unknown gate = %q, want fallback %q", got, "4")
	}
}

func TestCVPDistanceHelper(t *testing.T) {
	p := parsePlan(t, chainYAML)
	if d, ok := CVPDistance(p, "4", "2"); !ok || d != 2 {
		t.Fatalf("CVPDistance(4,2) = (%d,%v), want (2,true)", d, ok)
	}
	if d, ok := CVPDistance(p, "", "2"); ok || d != -1 {
		t.Fatalf("CVPDistance with no gate = (%d,%v), want (-1,false)", d, ok)
	}
}

// marginalDiamondYAML is a five-node plan shaped like a diamond with one
// branch that does not reach the checkpoint. Node 3 is the sibling of node 2:
// same estimate, same distance from the start, but nothing downstream of it
// sits on the way to the gate, so no work it does moves the checkpoint
// forward.
const marginalDiamondYAML = `
version: 1
run: marginal
defaults:
  estimate: 10m
nodes:
  - id: "1"
    kind: INTENT
    title: "Frame the work"
    estimate: 5m
  - id: "2"
    kind: SPEC
    title: "Write the spec"
    deps: ["1"]
    estimate: 10m
  - id: "3"
    kind: RESEARCH
    title: "Survey the alternatives"
    deps: ["1"]
    estimate: 10m
  - id: "4"
    kind: IMPL
    title: "Build it"
    deps: ["2"]
    estimate: 20m
  - id: "5"
    kind: GATE
    title: "Ship gate"
    deps: ["4"]
    estimate: 5m
    check: "true"
`

func TestMarginalScoreOnPathBeatsOffPathSibling(t *testing.T) {
	p := parsePlan(t, marginalDiamondYAML)
	if gate := CVPGate(p); gate != "5" {
		t.Fatalf("CVPGate = %q, want %q", gate, "5")
	}

	onPath := MarginalScore(p, "2")
	offPath := MarginalScore(p, "3")
	if !(onPath > offPath) {
		t.Fatalf("marginal score of on-path node 2 = %v, off-path node 3 = %v; want on-path higher", onPath, offPath)
	}
	if offPath != 0 {
		t.Errorf("marginal score of node 3 = %v, want 0 (nothing it does reaches the checkpoint)", offPath)
	}
	// The best opportunity in the plan is normalised to 1.
	if best := MarginalScore(p, "1"); best != 1 {
		t.Errorf("marginal score of node 1 = %v, want 1 (best in plan)", best)
	}
	// Node 4 unlocks only the gate, so it must score below node 2, which
	// unlocks the implementation and the gate.
	if MarginalScore(p, "4") >= onPath {
		t.Errorf("marginal score of node 4 = %v, want below node 2 (%v)", MarginalScore(p, "4"), onPath)
	}
}

func TestMarginalScoreIsClampedAndStable(t *testing.T) {
	p := parsePlan(t, marginalDiamondYAML)
	for _, id := range []string{"1", "2", "3", "4", "5", "nope"} {
		first := MarginalScore(p, id)
		second := MarginalScore(p, id)
		if first != second {
			t.Errorf("node %s: score changed between calls: %v vs %v", id, first, second)
		}
		if first < 0 || first > 1 {
			t.Errorf("node %s: score = %v, want within [0,1]", id, first)
		}
	}
}

func TestMarginalScoreWithoutGateIsZero(t *testing.T) {
	p := parsePlan(t, `
version: 1
run: no-gate
nodes:
  - id: "1"
    kind: INTENT
  - id: "2"
    kind: IMPL
    deps: ["1"]
`)
	if got := MarginalScore(p, "1"); got != 0 {
		t.Errorf("marginal score without a checkpoint = %v, want 0", got)
	}
}

func TestMarginalScoreUsesPlanDefaultForMissingEstimate(t *testing.T) {
	// A hand-built plan never went through Parse, so no node carries an
	// estimate and the plan declares no default. Scoring must not panic and
	// must not divide by zero.
	p := &Plan{
		Nodes: []*Node{
			{ID: "1", Kind: "INTENT"},
			{ID: "2", Kind: "IMPL", Deps: []string{"1"}},
			{ID: "3", Kind: "GATE", Deps: []string{"2"}},
		},
	}
	for _, id := range []string{"1", "2", "3"} {
		got := MarginalScore(p, id)
		if got < 0 || got > 1 {
			t.Errorf("node %s: score = %v, want within [0,1]", id, got)
		}
	}
	if MarginalScore(p, "2") <= 0 {
		t.Errorf("node 2: score = %v, want a positive score (it unlocks the gate)", MarginalScore(p, "2"))
	}
}

func TestMarginalScoreUsesPlanDefaultEstimate(t *testing.T) {
	// The plan default is 30m here and node 2 declares none, so node 2 costs
	// 30 minutes: unlocking the 5m gate buys 5/30 of a minute of work.
	p := parsePlan(t, `
version: 1
run: default-estimate
defaults:
  estimate: 30m
nodes:
  - id: "1"
    kind: INTENT
    estimate: 5m
  - id: "2"
    kind: IMPL
    deps: ["1"]
  - id: "3"
    kind: GATE
    deps: ["2"]
    estimate: 5m
    check: "true"
`)
	got := MarginalScore(p, "2")
	if got <= 0 || got > 1 {
		t.Fatalf("node 2: score = %v, want a score within (0,1]", got)
	}
	// node 1 unlocks 30m + 5m = 35m for 5m of its own work, node 2 unlocks
	// 5m for 30m of its own work, so node 1 must win.
	if MarginalScore(p, "1") <= got {
		t.Errorf("node 1 score = %v, want above node 2 (%v)", MarginalScore(p, "1"), got)
	}
}

func TestLessCVPOrderKeyTieFallsBackToDistanceThenID(t *testing.T) {
	cases := []struct {
		name string
		a, b CVPOrderKey
		want bool // whether a sorts before b
	}{
		{
			name: "higher marginal score wins",
			a:    CVPOrderKey{ID: "2", Marginal: 0.5},
			b:    CVPOrderKey{ID: "1", Marginal: 0.2},
			want: true,
		},
		{
			name: "equal marginal score falls back to the checkpoint path",
			a:    CVPOrderKey{ID: "2", Marginal: 0.5, OnPath: true},
			b:    CVPOrderKey{ID: "1", Marginal: 0.5, OnPath: false},
			want: true,
		},
		{
			name: "equal marginal score and path falls back to distance",
			a:    CVPOrderKey{ID: "2", Marginal: 0.5, OnPath: true, Distance: 3},
			b:    CVPOrderKey{ID: "1", Marginal: 0.5, OnPath: true, Distance: 1},
			want: false,
		},
		{
			name: "everything equal falls back to the id",
			a:    CVPOrderKey{ID: "1", Marginal: 0.5, OnPath: true, Distance: 2},
			b:    CVPOrderKey{ID: "2", Marginal: 0.5, OnPath: true, Distance: 2},
			want: true,
		},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			if got := LessCVPOrderKey(c.a, c.b); got != c.want {
				t.Errorf("LessCVPOrderKey(%+v, %+v) = %v, want %v", c.a, c.b, got, c.want)
			}
		})
	}
}

func TestCVPOrderKeySortIsTotalAndReproducible(t *testing.T) {
	p := parsePlan(t, marginalDiamondYAML)
	gate := CVPGate(p)
	scores := MarginalScoresFor(p, gate)

	keys := make([]CVPOrderKey, 0, len(p.Nodes))
	for _, n := range p.Sorted() {
		dist, onPath := CVPDistance(p, gate, n.ID)
		keys = append(keys, CVPOrderKey{ID: n.ID, Marginal: scores[n.ID], OnPath: onPath, Distance: dist})
	}
	sort.SliceStable(keys, func(i, j int) bool { return LessCVPOrderKey(keys[i], keys[j]) })

	// Node 1 releases the most checkpoint work per minute, so it leads.
	if keys[0].ID != "1" {
		t.Errorf("first ready node = %q, want %q (highest marginal score)", keys[0].ID, "1")
	}
	pos := map[string]int{}
	for i, k := range keys {
		pos[k.ID] = i
	}
	// Node 2 unlocks the implementation and the gate; node 3 unlocks
	// nothing, so node 2 comes first even though node 3 sits no further from
	// the checkpoint than node 2 does.
	if pos["2"] > pos["3"] {
		t.Errorf("node 2 at %d, node 3 at %d; want node 2 first (higher marginal score)", pos["2"], pos["3"])
	}
	// The order is total: sorting twice gives the same sequence.
	again := append([]CVPOrderKey(nil), keys...)
	sort.SliceStable(again, func(i, j int) bool { return LessCVPOrderKey(again[i], again[j]) })
	for i := range keys {
		if keys[i] != again[i] {
			t.Fatalf("sort is not reproducible at %d: %+v vs %+v", i, keys[i], again[i])
		}
	}
}
