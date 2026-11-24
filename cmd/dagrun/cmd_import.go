package main

import (
	"fmt"
	"io"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"

	"github.com/KooshaPari/dagrun/internal/agileplus"
	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/tracera"
)

// cmdImport reconstructs a plan from a payload and writes it as YAML to --out
// (or stdout). Anything that could not be represented is reported on stderr,
// never dropped silently.
//
// Two sources exist because dagrun has two interop directions: Tracera, which
// carries an execution record, and AgilePlus, which carries a feature and its
// work packages. They are not the same shape and pretending otherwise would
// lose whichever one did not win.
func cmdImport(args []string) error {
	var dir, in, out string
	var jsonOut bool
	fs := flagSet("import", &dir, &jsonOut)
	fs.StringVar(&in, "in", "-", "input file; - for stdin")
	fs.StringVar(&out, "out", "", "output file; empty writes to stdout")
	from := fs.String("from", "tracera", "payload source: tracera | agileplus")
	mapPath := fs.String("map", "", "AgilePlus id map to write, so a re-import keeps node identity (default <dir>/agileplus.map.json)")
	if err := fs.Parse(args); err != nil {
		return err
	}

	var data []byte
	var err error
	if in == "-" {
		data, err = readAllStdin()
	} else {
		data, err = os.ReadFile(in)
	}
	if err != nil {
		return fmt.Errorf("read input: %w", err)
	}

	var p *plan.Plan
	switch *from {
	case "tracera":
		res, err := tracera.ImportJSON(data)
		if err != nil {
			// Still print whatever was reconstructed, to aid debugging.
			if res.Plan != nil {
				for _, d := range res.Dropped {
					fmt.Fprintf(os.Stderr, "dropped: %s\n", d)
				}
			}
			return err
		}
		for _, d := range res.Dropped {
			fmt.Fprintf(os.Stderr, "dropped: %s\n", d)
		}
		p = res.Plan
	case "agileplus":
		next, unmapped, err := agileplus.FromJSON(data)
		if err != nil {
			return err
		}
		for _, u := range unmapped {
			fmt.Fprintf(os.Stderr, "unmapped: %s#%d %q: %s\n", u.Feature, u.Sequence, u.Title, u.Reason)
		}
		// The id map is what makes a re-import recognise "this is the same work,
		// edited" instead of "this is new work".
		mp := *mapPath
		if mp == "" {
			mp = filepath.Join(dir, "agileplus.map.json")
		}
		idm, err := agileplus.LoadIDMap(mp)
		if err != nil {
			return err
		}
		for _, n := range next.Nodes {
			if n == nil {
				continue
			}
			if seq, ok := agileplus.SequenceOf(n.ID); ok {
				idm.Set(next.Run, seq, n.ID)
			}
		}
		if err := idm.Save(mp); err != nil {
			return fmt.Errorf("write id map: %w", err)
		}
		p = next
	default:
		return fmt.Errorf("--from %q: expected tracera or agileplus", *from)
	}

	if p == nil {
		return fmt.Errorf("nothing was reconstructed from the payload")
	}
	if issues := p.Validate(); len(issues) > 0 {
		// A reconstructed plan that does not validate is still printed: the
		// caller needs to see what the import produced in order to fix the
		// source. The failure is reported, not hidden.
		for _, is := range issues {
			fmt.Fprintf(os.Stderr, "invalid: %s\n", is)
		}
	}

	raw, err := yaml.Marshal(p)
	if err != nil {
		return err
	}

	if out == "" {
		if _, err := os.Stdout.Write(append(raw, '\n')); err != nil {
			return err
		}
	} else if err := os.WriteFile(out, append(raw, '\n'), 0o644); err != nil {
		return err
	}
	return nil
}

func readAllStdin() ([]byte, error) {
	return io.ReadAll(os.Stdin)
}
