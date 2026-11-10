package main

import (
	"fmt"
	"os"

	"github.com/KooshaPari/dagrun/internal/otel"
)

// cmdOtel emits the run as OTLP/JSON spans.
//
// It is an exporter, not a client: dagrun never opens a connection to a
// collector. The reason is the same one that keeps state in a JSON file — a
// tool that every agent process depends on should not fail because a sidecar is
// down. Emit the document, let the collector come and get it.
func cmdOtel(args []string) error {
	var dir string
	flags, _ := splitArgs(args)
	fs := flagSet("otel", &dir, nil)
	out := fs.String("out", "", "write here instead of stdout")
	if err := fs.Parse(flags); err != nil {
		return err
	}

	spans, err := otel.Build(dir)
	if err != nil {
		return err
	}

	w := os.Stdout
	if *out != "" {
		f, cerr := os.Create(*out)
		if cerr != nil {
			return cerr
		}
		defer f.Close()
		w = f
	}
	if err := otel.Write(w, spans); err != nil {
		return err
	}
	if *out != "" {
		fmt.Fprintf(os.Stderr, "wrote %d span(s) to %s\n", len(spans), *out)
	}
	return nil
}
