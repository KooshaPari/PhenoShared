package main

import (
	"context"
	"encoding/json"
	"errors"

	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"

	"github.com/KooshaPari/dagrun/internal/applet"
	"github.com/KooshaPari/dagrun/internal/server"
)

const serveHelp = `usage: dagrun serve [--dir DIR] [--addr A] [--embed-allow-origin O]... [--open] [--json]

Run the local read-only server for an installed run until interrupted.

The server never changes the run. It serves the live DAG viewer at / and a small
JSON API beside it (/api/health, /api/plan, /api/status, /api/query,
/api/nodes/{id}), so a viewer or a script can watch progress without reading
` + defaultDir + `/state.json by hand. The viewer re-renders itself when the run
state changes; there is no websocket and no SSE, which is why there is no
interval to configure.

Three applet routes publish this instance to a master console:

  /.well-known/applet.json   manifest, valid against urn:phenotype:atlas-plan:1:applet
  /api/applet                manifest + origin, mount, auth and data authority
  /embed                     embeddable read-only view (framed by a console)

  --dir DIR                   run directory (default .dagrun)
  --addr A                    listen address (default 127.0.0.1:0, loopback + ephemeral port)
  --embed-allow-origin O      let origin O frame /embed; repeatable. Default is
                              same-origin only. O is a bare origin such as
                              https://console.example:8443, never a wildcard.
  --open                      open the viewer URL in the OS default handler (darwin only)
  --json                      print the ready line as one JSON object instead of prose
  --check                     report whether this directory could be served, and exit.
                              Binds and releases the port, so it also proves the
                              address is free and the manifest is conforming.
                              Exit 0 = servable, 1 = not servable. Combines with
                              --json for a machine answer. The JSON names the
                              run directory as "dir" and "run_dir", and the
                              registry as "instance_dir": "dir" is overloaded
                              across commands and the second names are not.

Why --embed-allow-origin is explicit and never a wildcard: this server has no
authentication, so a frameable /embed hands the run's titles, statuses and agent
session ids to whatever origin is allowed. Loopback binding is the security
boundary, and an allow-listed origin crosses it, so it is named by a human.

On success it prints exactly one line to stdout, e.g.

  serving http://127.0.0.1:52341/  (dir /abs/path/.dagrun)

so a caller can find the URL without filtering stderr. Ctrl-C (or SIGTERM)
stops the server and exits 0.

--check exists for a supervisor or a tray icon. Without it the only way to learn
that a directory cannot be served was to start the server and watch every request
fail to connect, which reads as a broken server rather than as a missing plan.
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
	checkOnly := fs.Bool("check", false, "report whether this directory could be served, then exit")
	// Repeatable, because a console may legitimately have a couple of origins
	// (a local dev server and the deployed one) and one flag with a comma list
	// would make an origin containing a comma unrepresentable. It is a
	// flag.Value because the flag package has no native repeated-string flag.
	var frames originsFlag
	fs.Var(&frames, "embed-allow-origin", "origin allowed to frame /embed; repeatable")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if *checkOnly {
		return servePreflight(dir, *addr, frames, jsonOut)
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

	// Advertise where a host that did not start this server can find it, so a
	// tray icon or a master console can list running instances without port
	// scanning. A missing registry directory costs a convenience, not the
	// server, so this warns and serves anyway.
	instanceDir, err := applet.DefaultInstanceDir()
	if err != nil {
		fmt.Fprintf(os.Stderr, "dagrun serve: this instance will not be discoverable: %v\n", err)
		instanceDir = ""
	}

	srv, err := server.New(server.Options{
		Dir:               abs,
		Addr:              *addr,
		Version:           Version,
		EmbedAllowOrigins: frames,
		InstanceDir:       instanceDir,
	})
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

// servePreflight answers "could this directory be served", without serving.
//
// It runs the same checks a real start runs, in the same order, and releases the
// port before returning so asking changes nothing. Verified worth having: a
// launcher that starts a server in a directory with no plan gets a clean exit, no
// listener, and then every request returns connection-refused, which reads as a
// broken server rather than a missing precondition. An answer to the question is
// not the same as silence followed by failure.
//
// A registry that cannot be resolved is a warning, not a failure, because it
// costs discoverability rather than the server: the real start warns and serves.
func servePreflight(dir, addr string, frames originsFlag, jsonOut bool) error {
	abs, err := filepath.Abs(dir)
	if err != nil {
		return err
	}
	// `dir` here is the RUN directory, while `dagrun instances --json` uses the
	// same key for the REGISTRY. Both are emitted under a second name so a
	// consumer never has to know which command it is reading: `run_dir` is the
	// run directory and `instance_dir` is the registry, here and there. Same
	// resolution as cmd_instances.go, which emits both rather than deprecating
	// one, and for the same reason: a launcher written against one key silently
	// decodes the other as empty and concludes "nothing here" rather than
	// failing.
	report := map[string]any{"dir": abs, "run_dir": abs, "addr": addr, "ok": false}
	var failure error

	planPath := filepath.Join(abs, "run.yaml")
	if _, err := os.Stat(planPath); err != nil {
		if os.IsNotExist(err) {
			failure = fmt.Errorf("no plan installed at %s; run `dagrun plan FILE` first", planPath)
		} else {
			failure = err
		}
	}
	if failure == nil {
		report["plan"] = planPath
	}

	instanceDir, instErr := applet.DefaultInstanceDir()
	if instErr != nil {
		report["instance_warning"] = instErr.Error()
		instanceDir = ""
	} else {
		report["instance_dir"] = instanceDir
	}

	// A bind is the only honest way to answer "is this address usable", and it is
	// also where an unconforming manifest is caught, because server.New builds and
	// validates one. The listener is released immediately either way.
	//
	// InstanceDir is deliberately left empty even when the registry resolves: Bind
	// advertises, and a preflight that advertised would leave a record for a server
	// that never serves. Retraction happens when Listen returns, which never
	// happens here. Measured: without this, one `--check` per poll filled the
	// registry with phantom servers, which is precisely the tray confusion the
	// registry exists to prevent.
	if failure == nil {
		srv, err := server.New(server.Options{
			Dir:               abs,
			Addr:              addr,
			Version:           Version,
			EmbedAllowOrigins: frames,
		})
		if err != nil {
			failure = err
		} else if err := srv.Bind(); err != nil {
			failure = fmt.Errorf("cannot listen on %s: %w", addr, err)
		} else {
			report["addr"] = srv.Addr()
			report["servable_url"] = "http://" + srv.Addr() + "/"
			if err := srv.Close(); err != nil {
				failure = err
			}
		}
	}

	if failure != nil {
		report["error"] = failure.Error()
	} else {
		report["ok"] = true
	}

	if jsonOut {
		if err := json.NewEncoder(os.Stdout).Encode(report); err != nil {
			return err
		}
	} else if failure == nil {
		fmt.Printf("servable %s  (dir %s)\n", report["servable_url"], abs)
	}
	// Prose failure prints nothing here: main already writes the error, once, to
	// stderr with the command name in front of it. Printing it here too made every
	// failed check say the same sentence twice.
	return failure
}

// originsFlag collects repeated --embed-allow-origin values.
//
// It does not validate them: validation is applet.FrameAncestors' job, called by
// server.New, so the rule lives next to the document that publishes the policy
// rather than being duplicated in the CLI.
type originsFlag []string

func (f *originsFlag) String() string { return strings.Join(*f, ",") }

func (f *originsFlag) Set(v string) error {
	*f = append(*f, v)
	return nil
}
