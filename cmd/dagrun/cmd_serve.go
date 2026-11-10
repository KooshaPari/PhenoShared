package main

import (
	"context"
	"encoding/json"
	"errors"

	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/KooshaPari/dagrun/internal/server"
)

const serveHelp = `usage: dagrun serve [--dir DIR] [--addr A] [--open] [--json]

Run the local read-only server for an installed run until interrupted.

The server never changes the run. It serves the live DAG viewer at / and a small
JSON API beside it (/api/health, /api/plan, /api/status, /api/query,
/api/nodes/{id}), so a viewer or a script can watch progress without reading
` + defaultDir + `/state.json by hand. The viewer re-renders itself when the run
state changes; there is no websocket and no SSE, which is why there is no
interval to configure.

  --dir DIR    run directory (default .dagrun)
  --addr A     listen address (default 127.0.0.1:0, loopback + ephemeral port)
  --open       open the viewer URL in the OS default handler (darwin only)
  --json       print the ready line as one JSON object instead of prose

On success it prints exactly one line to stdout, e.g.

  serving http://127.0.0.1:52341/  (dir /abs/path/.dagrun)

so a caller can find the URL without filtering stderr. Ctrl-C (or SIGTERM)
stops the server and exits 0.
`

// cmdServe runs the read-only HTTP server for one run directory.
//
// Flags are parsed directly rather than through splitArgs: --addr takes a
// value, and splitArgs only knows the flags listed in its valueFlags map, so it
// would strand that value as a positional. cmd_viz makes the same choice for the
// same reason.
//
// The ready line goes to stdout BEFORE Listen blocks, because the port is
// already known once server.New has bound the listener. Printing it after the
// call returns would tell nobody anything: Listen only returns when the server
// stops.
func cmdServe(args []string) error {
	if hasHelp(args) {
		fmt.Fprint(os.Stdout, serveHelp)
		return nil
	}
	var dir string
	var jsonOut bool
	fs := flagSet("serve", &dir, &jsonOut)
	addr := fs.String("addr", "127.0.0.1:0", "listen address; :0 picks an ephemeral port")
	openIt := fs.Bool("open", false, "open the viewer URL (darwin only)")
	if err := fs.Parse(args); err != nil {
		return err
	}

	// Refuse before binding a port: a server with no plan has nothing to serve,
	// and the error has to say which command installs one.
	abs, err := filepath.Abs(dir)
	if err != nil {
		return err
	}
	planPath := filepath.Join(abs, "run.yaml")
	if _, err := os.Stat(planPath); err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("no plan installed at %s; run `dagrun plan FILE` first", planPath)
		}
		return err
	}

	srv, err := server.New(server.Options{Dir: abs, Addr: *addr})
	if err != nil {
		return err
	}
	// Bind before announcing: the port is ephemeral unless the caller pinned
	// one, so the URL only exists once the listener does.
	if err := srv.Bind(); err != nil {
		return err
	}

	// Ctrl-C on a server is a normal stop, not a failure. NotifyContext turns
	// both the interactive interrupt and a supervisor's SIGTERM into a context
	// cancellation that Listen can unwind cleanly.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// Addr() is the bound address, so an ephemeral :0 port is reported as the
	// port that was actually granted.
	url := "http://" + srv.Addr() + "/"
	if jsonOut {
		enc := json.NewEncoder(os.Stdout)
		if err := enc.Encode(map[string]string{
			"url":  url,
			"dir":  abs,
			"addr": srv.Addr(),
		}); err != nil {
			return err
		}
	} else {
		fmt.Printf("serving %s  (dir %s)\n", url, abs)
	}

	if *openIt {
		// Reuses the viz helper: it hands the target to the desktop on darwin
		// and is a no-op elsewhere, where there is no handler to invoke.
		openVizFile(url)
	}

	if err := srv.Listen(ctx); err != nil {
		// A cancelled context can surface as an error on some listener loops;
		// that still means "we were asked to stop", not "we failed".
		if !errors.Is(err, context.Canceled) {
			return err
		}
	}
	fmt.Fprintln(os.Stderr, "stopped")
	return nil
}
