package main

import (
	"encoding/json"
	"flag"
	"os"

	"github.com/KooshaPari/dagrun/internal/stats"
)

// cmdStats prints per-kind duration, adoption and retry statistics.
//
// The computation lives in internal/stats so a report is data other surfaces
// can consume; this command is only flag parsing and output selection.
//
// Tokens are only counted when a harness actually reported usage; when none
// did, the report says so rather than printing a zero that reads as "free".
func cmdStats(args []string) error {
	fs := flag.NewFlagSet("stats", flag.ContinueOnError)
	fs.SetOutput(os.Stderr)
	dir := fs.String("dir", defaultDir, "run directory")
	jsonOut := fs.Bool("json", false, "machine-readable output on stdout")
	if err := fs.Parse(args); err != nil {
		return err
	}
	r, err := stats.Compute(*dir)
	if err != nil {
		return err
	}
	if *jsonOut {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		return enc.Encode(r)
	}
	return stats.Render(os.Stdout, r)
}
