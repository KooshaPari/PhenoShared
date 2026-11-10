package main

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

func cmdPlan(args []string) error {
	var dir string
	var jsonOut bool
	flags, pos := splitArgs(args)
	fs := flagSet("plan", &dir, &jsonOut)
	file := fs.String("file", "", "plan source, - for stdin")
	reset := fs.Bool("reset", false, "discard existing progress")
	work := fs.Int("work", 0, "worker count for the wall-clock estimate")
	from := fs.String("from", "auto", "plan format: auto | dagrun | dagschema")
	if err := fs.Parse(flags); err != nil {
		return err
	}

	src := *file
	if src == "" && len(pos) > 0 {
		src = pos[0]
	}
	if src == "" {
		src = filepath.Join(dir, "run.yaml")
	}

	var raw []byte
	var err error
	if src == "-" {
		raw, err = io.ReadAll(os.Stdin)
	} else {
		raw, err = os.ReadFile(src)
	}
	if err != nil {
		return err
	}

	// Which schema is this? `auto` detects a phenotype-dag-core DagSchema by
	// its `edges:` list, which a dagrun plan never has: a plan expresses
	// dependency through node `deps`, so an `edges` key can only be the other
	// schema. Guessing wrong here would reject a valid document with a
	// confusing message, so the flag exists to override the guess.
	format := *from
	if format == "auto" {
		format = "dagrun"
		if looksLikeDagSchema(raw) {
			format = "dagschema"
		}
	}

	var p *plan.Plan
	switch format {
	case "dagrun":
		p, err = plan.Parse(raw)
		if err != nil {
			return fmt.Errorf("parse: %w", err)
		}
	case "dagschema":
		d, derr := plan.ParseDagSchema(raw)
		if derr != nil {
			return derr
		}
		converted, unmapped, derr := d.ToPlan()
		if derr != nil {
			return derr
		}
		for _, u := range unmapped {
			// Reported, never dropped: an unmappable field that vanished
			// silently is how two schemas drift back apart.
			fmt.Fprintf(os.Stderr, "unmapped: node %s: %s: %s\n", u.Node, u.Field, u.Detail)
		}
		p = converted
	default:
		return fmt.Errorf("--from %q: expected auto, dagrun or dagschema", *from)
	}
	cwd, err := os.Getwd()
	if err != nil {
		return err
	}
	p.Root = cwd

	if issues := p.Validate(); len(issues) > 0 {
		if jsonOut {
			enc := json.NewEncoder(os.Stdout)
			enc.SetIndent("", "  ")
			_ = enc.Encode(map[string]any{"ok": false, "issues": issues})
		} else {
			fmt.Fprintf(os.Stderr, "plan is not runnable: %d issue(s)\n", len(issues))
			for _, is := range issues {
				fmt.Fprintf(os.Stderr, "  - %s\n", is)
			}
		}
		return fmt.Errorf("plan rejected")
	}

	abs, err := filepath.Abs(dir)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(abs, 0o755); err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(abs, "run.yaml"), raw, 0o644); err != nil {
		return err
	}

	st, err := store.Open(abs, p, raw, *reset)
	if err != nil {
		return err
	}
	snap, err := st.Snapshot()
	if err != nil {
		return err
	}

	if jsonOut {
		sched := p.Pert()
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		return enc.Encode(map[string]any{
			"ok":         true,
			"run":        p.Run,
			"dir":        abs,
			"root":       p.Root,
			"nodes":      len(p.Nodes),
			"waves":      sched.Waves,
			"critical":   sched.Critical,
			"total":      sched.Total.String(),
			"wallclock":  wallclockMap(sched, *work),
			"state_file": filepath.Join(abs, "state.json"),
			"adopted":    alreadyDone(snap, p),
		})
	}

	var b strings.Builder
	p.RenderPlan(&b, *work)
	fmt.Print(b.String())
	fmt.Printf("\ninstalled plan at %s\n", filepath.Join(abs, "run.yaml"))
	fmt.Printf("artifacts resolve under %s\n", p.Root)
	if n := alreadyDone(snap, p); n > 0 {
		fmt.Printf("%d node(s) already recorded as done from a previous run\n", n)
	}
	return nil
}

func wallclockMap(s *plan.Schedule, work int) map[string]string {
	out := map[string]string{}
	for w, d := range s.Wallclock {
		out[fmt.Sprintf("%d", w)] = d.String()
	}
	return out
}

func alreadyDone(snap *store.State, p *plan.Plan) int {
	n := 0
	for _, node := range p.Nodes {
		if node == nil {
			continue
		}
		if ns := snap.Nodes[node.ID]; ns != nil && ns.Status == plan.StatusDone {
			n++
		}
	}
	return n
}

// looksLikeDagSchema reports whether the document is a phenotype-dag-core
// DagSchema rather than a dagrun plan. The discriminator is the `edges` key: a
// dagrun plan has no top-level edges, it puts dependencies on each node.
func looksLikeDagSchema(raw []byte) bool {
	for _, line := range strings.Split(string(raw), "\n") {
		if strings.HasPrefix(line, "edges:") {
			return true
		}
	}
	return false
}
