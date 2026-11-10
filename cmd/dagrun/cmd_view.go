package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/KooshaPari/dagrun/internal/export"
	"github.com/KooshaPari/dagrun/internal/harness"
	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
	"github.com/KooshaPari/dagrun/internal/trace"
)

func cmdStatus(args []string) error {
	var dir string
	var jsonOut bool
	flags, _ := splitArgs(args)
	fs := flagSet("status", &dir, &jsonOut)
	watch := fs.Duration("watch", 0, "redraw every interval until every node is terminal, e.g. 2s")
	plain := fs.Bool("watch-plain", false, "when watching, print a separator instead of using ANSI cursor control")
	if err := fs.Parse(flags); err != nil {
		return err
	}
	if *watch > 0 && jsonOut {
		return fmt.Errorf("--watch and --json cannot be combined: a stream of JSON documents is not readable and not parseable")
	}
	p, st, _, err := openRun(dir)
	if err != nil {
		return err
	}
	if *watch > 0 {
		return watchStatus(p, st, *watch, *plain)
	}
	return printStatus(p, st, jsonOut)
}

// watchStatus redraws until every node reaches a terminal state, so an operator
// can watch a run without polling by hand. It stops on its own: a watcher that
// runs forever is a process someone forgets to kill.
func watchStatus(p *plan.Plan, st *store.Store, every time.Duration, plain bool) error {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	tty := !plain && isTTY(os.Stdout)
	tick := time.NewTicker(every)
	defer tick.Stop()

	for {
		if tty {
			// Move home and clear below, so the frame count never grows.
			fmt.Print("\033[H\033[2J")
		} else if plain {
			fmt.Printf("--- %s ---\n", time.Now().Format("15:04:05"))
		}
		if err := printStatus(p, st, false); err != nil {
			return err
		}
		snap, err := st.Snapshot()
		if err != nil {
			return err
		}
		if allTerminal(st, snap) {
			return nil
		}
		select {
		case <-ctx.Done():
			fmt.Println("\nstopped watching")
			return nil
		case <-tick.C:
		}
	}
}

// allTerminal reports whether every node has finished, one way or another. A
// run with no nodes is not terminal: nothing ran yet.
func allTerminal(st *store.Store, snap *store.State) bool {
	all := st.All(snap)
	if len(all) == 0 {
		return false
	}
	for _, n := range all {
		ns := snap.Nodes[n.ID]
		if ns == nil {
			return false
		}
		switch ns.Status {
		case plan.StatusDone, plan.StatusFailed, plan.StatusSkipped, plan.StatusCancelled:
		default:
			return false
		}
	}
	return true
}

func isTTY(f *os.File) bool {
	info, err := f.Stat()
	if err != nil {
		return false
	}
	return info.Mode()&os.ModeCharDevice != 0
}

func printStatus(p *plan.Plan, st *store.Store, jsonOut bool) error {
	snap, err := st.Snapshot()
	if err != nil {
		return err
	}
	if jsonOut {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		return enc.Encode(snap)
	}

	all := st.All(snap)
	counts := map[string]int{}
	for _, n := range all {
		if ns := snap.Nodes[n.ID]; ns != nil {
			counts[ns.Status]++
		}
	}

	var b strings.Builder
	fmt.Fprintf(&b, "run %s   nodes %d\n", p.Run, len(all))
	// fixed order so output is diffable
	for _, s := range []string{plan.StatusDone, plan.StatusRunning, plan.StatusPending, plan.StatusFailed, plan.StatusSkipped, plan.StatusCancelled} {
		if counts[s] > 0 {
			fmt.Fprintf(&b, "  %-10s %d\n", s, counts[s])
		}
	}
	b.WriteString("\n")

	for _, n := range all {
		ns := snap.Nodes[n.ID]
		if ns == nil {
			continue
		}
		glyph := statusGlyph(ns.Status)
		extra := ""
		if ns.Attempts > 1 {
			extra = fmt.Sprintf(" attempt=%d", ns.Attempts)
		}
		if ns.Status == plan.StatusRunning && ns.Owner != "" {
			extra += " owner=" + ns.Owner
		}
		if ns.Branch != "" {
			extra += " on " + ns.Branch
		}
		if ns.LastError != "" && (ns.Status == plan.StatusFailed || ns.Status == plan.StatusPending) {
			extra += " " + truncate(ns.LastError, 70)
		}
		arts := 0
		if ns.Verify != nil {
			for _, a := range ns.Verify.Artifacts {
				if a.OK {
					arts++
				}
			}
		}
		fmt.Fprintf(&b, "%s %-8s %-9s %-6s %d/%d %s%s\n",
			glyph, n.ID, n.Kind, n.Estimate, arts, len(n.Artifacts), n.Title, extra)
	}

	// Fan-out templates are structure, not work: exclude them from progress.
	done, total := counts[plan.StatusDone], 0
	for _, n := range all {
		if n.FanOut == "" {
			total++
		}
	}
	pct := 0
	if total > 0 {
		pct = done * 100 / total
	}
	b.WriteString("\n")
	fmt.Fprintf(&b, "progress %d/%d (%d%%)\n", done, total, pct)
	fmt.Print(b.String())
	return nil
}

// filterEvents narrows a merged trace. Order of application is fixed so the
// answer does not depend on flag order: since, then node, then event, then limit.
// A limit applies to the tail, because "the last N" is the question an operator
// actually asks when a run is noisy.
func filterEvents(events []trace.Event, node, event, since string, limit int) ([]trace.Event, error) {
	var cutoff time.Time
	switch {
	case since == "":
	case strings.ContainsAny(since, "-:T"):
		t, err := time.Parse(time.RFC3339, since)
		if err != nil {
			return nil, fmt.Errorf("--since %q is not RFC3339 (want e.g. 2026-11-02T08:00:00Z) nor a duration like 30m: %w", since, err)
		}
		cutoff = t
	default:
		d, err := time.ParseDuration(since)
		if err != nil {
			return nil, fmt.Errorf("--since %q is not a duration (30m) or RFC3339: %w", since, err)
		}
		cutoff = time.Now().Add(-d)
	}

	out := make([]trace.Event, 0, len(events))
	for _, e := range events {
		if !cutoff.IsZero() && e.TS.Before(cutoff) {
			continue
		}
		if node != "" && !globMatch(node, e.Node) {
			continue
		}
		if event != "" && !globMatch(event, e.Event) {
			continue
		}
		out = append(out, e)
	}
	if limit > 0 && len(out) > limit {
		out = out[len(out)-limit:]
	}
	if limit < 0 {
		return nil, fmt.Errorf("--limit must not be negative")
	}
	return out, nil
}

// globMatch is a tiny *,? matcher. It exists so `--event 'node.*'` works without
// pulling path semantics in: a trace event name is not a filesystem path, and
// filepath.Match would treat a backslash as an escape on one platform only.
func globMatch(pattern, s string) bool {
	if pattern == "" {
		return true
	}
	pi, si := 0, 0
	star, mark := -1, 0
	for si < len(s) {
		switch {
		case pi < len(pattern) && (pattern[pi] == '?' || pattern[pi] == s[si]):
			pi++
			si++
		case pi < len(pattern) && pattern[pi] == '*':
			star, mark = pi, si
			pi++
		case star >= 0:
			pi = star + 1
			mark++
			si = mark
		default:
			return false
		}
	}
	for pi < len(pattern) && pattern[pi] == '*' {
		pi++
	}
	return pi == len(pattern)
}

func cmdTrace(args []string) error {
	var dir string
	var jsonOut bool
	flags, _ := splitArgs(args)
	fs := flagSet("trace", &dir, &jsonOut)
	node := fs.String("node", "", "only events for this node id (glob)")
	event := fs.String("event", "", "only events whose name matches this glob, e.g. node.* or *.fail")
	since := fs.String("since", "", "only events at or after this time: a duration back from now (30m) or RFC3339")
	limit := fs.Int("limit", 0, "keep only the last N events (0 = all)")
	if err := fs.Parse(flags); err != nil {
		return err
	}
	st, err := os.Stat(dir)
	if err != nil || !st.IsDir() {
		return fmt.Errorf("no run directory at %s", dir)
	}
	events, err := trace.Merge(dir + "/trace")
	if err != nil {
		return err
	}
	events, err = filterEvents(events, *node, *event, *since, *limit)
	if err != nil {
		return err
	}
	if jsonOut {
		enc := json.NewEncoder(os.Stdout)
		for _, e := range events {
			if err := enc.Encode(e); err != nil {
				return err
			}
		}
		return nil
	}
	if len(events) == 0 {
		fmt.Println("no events yet")
		return nil
	}
	fmt.Print(trace.Render(events))
	return nil
}

func cmdExport(args []string) error {
	var dir string
	flags, _ := splitArgs(args)
	fs := flagSet("export", &dir, nil)
	out := fs.String("out", "", "write to file instead of stdout")
	format := fs.String("format", "json", "agileplus | tracera | json")
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
	events, err := trace.Merge(st.Dir() + "/trace")
	if err != nil {
		return err
	}
	in := export.Input{Plan: p, State: snap, Events: events}

	var data []byte
	switch strings.ToLower(*format) {
	case "agileplus", "agile-plus", "ap":
		data, err = export.AgilePlus(in)
	case "tracera", "trace":
		data, err = export.Tracera(in)
	case "json":
		data, err = export.JSON(in)
	default:
		return fmt.Errorf("unknown format %q; want agileplus, tracera, or json", *format)
	}
	if err != nil {
		return err
	}
	data = append(data, '\n')
	if *out != "" {
		return os.WriteFile(*out, data, 0o644)
	}
	_, err = os.Stdout.Write(data)
	return err
}

func cmdDetect(args []string) error {
	var dir string
	var jsonOut bool
	flags, _ := splitArgs(args)
	fs := flagSet("detect", &dir, &jsonOut)
	if err := fs.Parse(flags); err != nil {
		return err
	}
	infos := harness.Detect()
	launching := harness.Launching()
	if jsonOut {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		return enc.Encode(map[string]any{"launching": launching, "harnesses": infos})
	}
	fmt.Printf("launching harness: %s\n\n", orUnknown(launching))
	fmt.Printf("%-12s %-8s %-26s %s\n", "NAME", "STATE", "VERSION", "PATH")
	for _, i := range infos {
		state := "missing"
		if i.Installed {
			state = "ok"
		}
		fmt.Printf("%-12s %-8s %-26s %s\n", i.Name, state, truncate(i.Version, 26), i.Path)
		if i.Note != "" && i.Installed {
			fmt.Printf("%-12s note: %s\n", "", i.Note)
		}
	}
	return nil
}

func orUnknown(s string) string {
	if s == "" {
		return "(unknown)"
	}
	return s
}
