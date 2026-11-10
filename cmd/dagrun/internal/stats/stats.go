// Package stats summarises a finished run: how much each kind of node did, how
// long it took, and how far the plan's estimates drifted from reality.
//
// The reason this is a package and not part of the CLI is the same reason
// internal/query exists: a report is data. Anything that can read a run
// directory (an MCP tool, a test, another command) should be able to produce
// the same numbers without shelling out to `dagrun stats` and scraping a table.
//
// Like query, the package is read-only by construction. It reads run.yaml and
// state.json directly and never opens the store, because store.Open creates
// directories and a report must not change the run it is reporting on.
package stats

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"time"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// Kind is one row of the per-kind table.
type Kind struct {
	Kind     string `json:"kind"`
	Nodes    int    `json:"nodes"`
	Done     int    `json:"done"`
	Failed   int    `json:"failed"`
	Retried  int    `json:"retried"`
	Adopted  int    `json:"adopted"`
	MedianMS int64  `json:"median_ms"`
}

// Report is the whole stats document.
type Report struct {
	Run       string           `json:"run"`
	Nodes     int              `json:"nodes"`
	Kinds     []Kind           `json:"kinds"`
	TotalMS   int64            `json:"total_ms"`
	Measured  int              `json:"measured"`
	Durations map[string]int64 `json:"-"`

	// The fields below carry what only the human table needs. They are
	// unexported on purpose: the exported shape above is a contract other lanes
	// code against, so the render-only detail must not leak into it or into the
	// JSON document.
	//
	// kindMeasured is parallel to Kinds and says whether that kind contributed
	// a duration sample at all. MedianMS alone cannot answer that, because the
	// contract reports 0 for "no samples" while the table must print "-".
	kindMeasured  []bool
	missing       int
	calibration   string
	budgetUSD     float64
	maxCostUSD    float64
	hasBudget     bool
	tokensIn      int
	tokensOut     int
	tokensTotal   int
	usageReported int
}

// Compute reads an installed run and produces the report.
//
// A run with no state.json is not an error: no node has started, so every node
// is pending, and saying so is the truth rather than a failure.
func Compute(dir string) (*Report, error) {
	p, state, err := load(dir)
	if err != nil {
		return nil, err
	}

	// pending is what a node with no recorded state means. It is shared because
	// nothing here mutates it.
	pending := &store.NodeState{Status: plan.StatusPending}

	type acc struct {
		kind Kind
		durs []int64
		used bool
	}
	byKind := map[string]*acc{}
	order := make([]string, 0, len(p.Nodes))
	r := &Report{
		Run:       p.Run,
		Durations: map[string]int64{},
	}
	var allDurs []int64
	usageReported := 0

	for _, n := range p.Sorted() {
		ns := pending
		if state != nil {
			ns = state.Nodes[n.ID]
			// A node the state has never heard of is skipped rather than
			// assumed pending: the store only omits dynamic nodes it never
			// materialised, and counting those would invent work.
			if ns == nil {
				continue
			}
		}

		a := byKind[n.Kind]
		if a == nil {
			a = &acc{kind: Kind{Kind: n.Kind}}
			byKind[n.Kind] = a
			order = append(order, n.Kind)
		}
		a.kind.Nodes++
		switch ns.Status {
		case plan.StatusDone:
			a.kind.Done++
		case plan.StatusFailed:
			a.kind.Failed++
		}
		if ns.Attempts > 1 {
			a.kind.Retried++
		}
		if ns.Status == plan.StatusDone && ns.Attempts == 0 {
			a.kind.Adopted++
		}
		if ns.DurationMS > 0 {
			r.Measured++
			allDurs = append(allDurs, ns.DurationMS)
			a.durs = append(a.durs, ns.DurationMS)
			a.used = true
			r.Durations[n.ID] = ns.DurationMS
		} else {
			r.missing++
		}
		if ns.Usage != nil {
			usageReported++
			r.tokensIn += ns.Usage.InputTokens
			r.tokensOut += ns.Usage.OutputTokens
			r.tokensTotal += ns.Usage.Total()
		}
	}

	// Kinds come out sorted by name. The map above exists to group; iterating it
	// into output would make the table order vary between runs.
	sort.Strings(order)
	r.Kinds = make([]Kind, 0, len(order))
	r.kindMeasured = make([]bool, 0, len(order))
	for _, name := range order {
		a := byKind[name]
		k := a.kind
		// percentile keeps the CLI's existing rule: nearest index at q of
		// len-1, so an even sample count takes the lower of the two middles.
		if a.used {
			k.MedianMS = percentile(a.durs, 0.5)
		}
		r.Kinds = append(r.Kinds, k)
		r.kindMeasured = append(r.kindMeasured, a.used)
		r.Nodes += k.Nodes
	}
	r.TotalMS = sumAll(allDurs)
	r.usageReported = usageReported

	// Calibration is only meaningful once something was measured, so an
	// unmeasured run says nothing about it rather than claiming a zero drift.
	var obs []plan.Observation
	for _, n := range p.Sorted() {
		if state == nil {
			break
		}
		ns := state.Nodes[n.ID]
		if ns == nil || ns.DurationMS <= 0 {
			continue
		}
		obs = append(obs, plan.Observation{
			NodeID:   n.ID,
			Kind:     n.Kind,
			Estimate: n.EstimateDuration(),
			Actual:   time.Duration(ns.DurationMS) * time.Millisecond,
			Attempts: ns.Attempts,
			Adopted:  ns.Attempts == 0,
		})
	}
	if len(obs) > 0 {
		r.calibration = plan.Calibrate(obs).Drift()
	}

	if p.MaxCostUSD > 0 {
		r.hasBudget = true
		r.maxCostUSD = p.MaxCostUSD
		r.budgetUSD = tokensToUSD(r.tokensIn, r.tokensOut, r.tokensTotal, p.Run)
	}
	return r, nil
}

// Render writes the human table. It is deterministic: nothing here ranges over
// a map, so the same report always renders to the same bytes.
func Render(w io.Writer, r *Report) error {
	if _, err := fmt.Fprintf(w, "run %s — %d node(s)\n\n", r.Run, r.Nodes); err != nil {
		return err
	}
	if _, err := fmt.Fprintf(w, "%-11s %5s %6s %7s %8s %9s %9s\n", "KIND", "NODES", "DONE", "FAILED", "RETRIED", "ADOPTED", "MEDIAN"); err != nil {
		return err
	}
	for i, k := range r.Kinds {
		ms := int64(-1)
		if i < len(r.kindMeasured) && r.kindMeasured[i] {
			ms = k.MedianMS
		}
		if _, err := fmt.Fprintf(w, "%-11s %5d %6d %7d %8d %9d %9s\n",
			k.Kind, k.Nodes, k.Done, k.Failed, k.Retried, k.Adopted, msOrDash(ms)); err != nil {
			return err
		}
	}
	if _, err := fmt.Fprintf(w, "\ntotal node time: %s (measured on %d node(s), %d without a recorded duration)\n",
		msOrDash(r.TotalMS), r.Measured, r.missing); err != nil {
		return err
	}
	if r.calibration != "" {
		if _, err := fmt.Fprintf(w, "\nestimate calibration\n%s\n", r.calibration); err != nil {
			return err
		}
	}
	if r.hasBudget {
		if _, err := fmt.Fprintf(w, "\nbudget: $%.2f of $%.2f spent\n", r.budgetUSD, r.maxCostUSD); err != nil {
			return err
		}
	}
	if r.usageReported > 0 {
		if _, err := fmt.Fprintf(w, "tokens: %d in, %d out, %d total (reported by %d node(s))\n",
			r.tokensIn, r.tokensOut, r.tokensTotal, r.usageReported); err != nil {
			return err
		}
		if done := r.doneCount(); done > 0 {
			if _, err := fmt.Fprintf(w, "tokens per done node: %d\n", r.tokensTotal/done); err != nil {
				return err
			}
		}
		return nil
	}
	_, err := fmt.Fprintln(w, "tokens: not reported by any harness")
	return err
}

func (r *Report) doneCount() int {
	n := 0
	for _, k := range r.Kinds {
		n += k.Done
	}
	return n
}

// load reads the plan and, when present, the state. This mirrors internal/query
// so both read-only surfaces agree about what a run directory means.
func load(dir string) (*plan.Plan, *store.State, error) {
	raw, err := os.ReadFile(filepath.Join(dir, "run.yaml"))
	if err != nil {
		return nil, nil, fmt.Errorf("read plan in %s: %w", dir, err)
	}
	p, err := plan.Parse(raw)
	if err != nil {
		return nil, nil, fmt.Errorf("parse plan in %s: %w", dir, err)
	}
	sraw, err := os.ReadFile(filepath.Join(dir, "state.json"))
	if err != nil {
		if os.IsNotExist(err) {
			return p, nil, nil
		}
		return nil, nil, err
	}
	var st store.State
	if err := json.Unmarshal(sraw, &st); err != nil {
		return nil, nil, fmt.Errorf("parse state.json in %s: %w", dir, err)
	}
	return p, &st, nil
}

func sumAll(v []int64) int64 {
	var s int64
	for _, x := range v {
		s += x
	}
	return s
}

// percentile returns the p-quantile of a slice; -1 when empty.
func percentile(v []int64, q float64) int64 {
	if len(v) == 0 {
		return -1
	}
	s := append([]int64(nil), v...)
	sort.Slice(s, func(i, j int) bool { return s[i] < s[j] })
	idx := int(q * float64(len(s)-1))
	if idx < 0 {
		idx = 0
	}
	return s[idx]
}

func msOrDash(ms int64) string {
	if ms < 0 {
		return "-"
	}
	return fmt.Sprintf("%dms", ms)
}

// tokensToUSD estimates spend from tokens using the default rate table. It is
// keyed by run name only because that is what the CLI has always done; the
// lookup falls back to the mid-range rate on a miss.
func tokensToUSD(in, out, _ int, run string) float64 {
	rate, ok := plan.DefaultRates[run]
	if !ok {
		rate = plan.Rate{InputPerMillion: 3, OutputPerMillion: 15}
	}
	return plan.Cost(plan.Spend{InputTokens: in, OutputTokens: out}, rate)
}
