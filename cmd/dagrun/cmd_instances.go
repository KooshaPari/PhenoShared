package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/KooshaPari/dagrun/internal/applet"
)

const instancesHelp = `usage: dagrun instances [--dir REGISTRY] [--verify] [--json]

List running dagrun servers that advertise themselves on this machine.

A server started by ` + "`dagrun serve`" + ` records its URLs in a small file under the
instance directory (default ` + "`$DAGRUN_INSTANCE_DIR`" + `, else <config>/dagrun/instances).
This command reads that directory, which is what a tray icon, a menu bar item or
a master console uses to find a server it did not start.

  --dir DIR   registry directory (default: the instance directory)
  --verify    fetch each manifest to confirm the server is actually alive
  --json      print the entries as JSON

The registry is a hint. A killed server leaves its file behind, so an entry
without --verify says "advertised", not "reachable".`

// instanceReport is one entry as printed, with the liveness result folded in.
//
// The fields are flat rather than nested so that a consumer can read a row
// without walking a tree, and `Reachable` is a pointer because "not checked" and
// "checked, dead" are different answers and collapsing them into false would
// report a server that was never contacted as dead.
type instanceReport struct {
	applet.Instance
	Reachable *bool  `json:"reachable,omitempty"`
	Error     string `json:"error,omitempty"`
}

// cmdInstances lists advertised servers. It is read-only: nothing here starts,
// stops or signals a server.
func cmdInstances(args []string) error {
	if hasHelp(args) {
		fmt.Fprint(os.Stdout, instancesHelp)
		return nil
	}
	// A plain FlagSet rather than flagSet(): --dir here is the REGISTRY
	// directory, not a run directory, and inheriting the run-directory default
	// would make `dagrun instances` silently look in .dagrun for instance files.
	fs := flag.NewFlagSet("instances", flag.ContinueOnError)
	fs.SetOutput(os.Stderr)
	registry := fs.String("dir", "", "registry directory (default: the instance directory)")
	verify := fs.Bool("verify", false, "fetch each manifest to confirm the server is alive")
	jsonOut := fs.Bool("json", false, "machine-readable JSON on stdout")
	if err := fs.Parse(args); err != nil {
		return err
	}

	where := *registry
	if where == "" {
		resolved, err := applet.DefaultInstanceDir()
		if err != nil {
			return err
		}
		where = resolved
	}

	instances, errs := applet.ReadInstances(where)
	reports := make([]instanceReport, 0, len(instances))
	for _, inst := range instances {
		rep := instanceReport{Instance: inst}
		if *verify {
			rep.Reachable, rep.Error = probeManifest(inst)
		}
		reports = append(reports, rep)
	}

	if *jsonOut {
		// Errors are part of the answer, not a side channel: a caller that saw
		// only the valid entries would believe a corrupt registry is empty.
		body := struct {
			Dir       string           `json:"dir"`
			Instances []instanceReport `json:"instances"`
			Errors    []string         `json:"errors"`
		}{Dir: where, Instances: reports, Errors: []string{}}
		for _, err := range errs {
			body.Errors = append(body.Errors, err.Error())
		}
		out, err := json.MarshalIndent(body, "", "  ")
		if err != nil {
			return err
		}
		fmt.Fprintf(os.Stdout, "%s\n", out)
		return nil
	}

	if len(reports) == 0 {
		fmt.Fprintf(os.Stdout, "no dagrun servers advertised in %s\n", where)
	} else {
		printInstances(reports)
	}
	// A bad file is reported and does not fail the command: the good entries are
	// still the answer, and a launcher must not treat one stale file as "no
	// server at all".
	for _, err := range errs {
		fmt.Fprintf(os.Stderr, "dagrun instances: skipping unreadable entry: %v\n", err)
	}
	return nil
}

func printInstances(reports []instanceReport) {
	rows := make([][5]string, 0, len(reports))
	for _, rep := range reports {
		reach := "-"
		switch {
		case rep.Reachable == nil:
			reach = "advertised"
		case *rep.Reachable:
			reach = "ok"
		default:
			reach = "unreachable"
		}
		rows = append(rows, [5]string{rep.ID, rep.Version, rep.Origin, rep.StartedAt, reach})
	}
	head := [5]string{"ID", "VERSION", "ORIGIN", "STARTED", "STATUS"}
	widths := [5]int{}
	for i, cell := range head {
		widths[i] = len(cell)
	}
	for _, row := range rows {
		for i, cell := range row {
			if len(cell) > widths[i] {
				widths[i] = len(cell)
			}
		}
	}
	printRow := func(row [5]string) {
		cells := make([]string, len(row))
		for i, cell := range row {
			cells[i] = cell + strings.Repeat(" ", widths[i]-len(cell))
		}
		fmt.Fprintf(os.Stdout, "%s\n", strings.TrimRight(strings.Join(cells, "  "), " "))
	}
	printRow(head)
	for _, row := range rows {
		printRow(row)
	}
}

// probeManifest confirms an advertised server by fetching its manifest.
//
// The URL comes from the record, which is why the record is validated to be
// loopback first: this is the one place the command actually makes a request,
// and it must never be talked into fetching an arbitrary host.
func probeManifest(inst applet.Instance) (*bool, string) {
	client := &http.Client{Timeout: 2 * time.Second}
	resp, err := client.Get(inst.Manifest)
	if err != nil {
		no := false
		return &no, err.Error()
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		no := false
		return &no, fmt.Sprintf("manifest returned %s", resp.Status)
	}
	// The contract document identifies itself by `id` and `version`: the contract
	// urn is the schema it conforms to, not a field it carries. Checking the
	// schema urn here would reject every real dagrun manifest.
	var manifest struct {
		ID      string `json:"id"`
		Version string `json:"version"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&manifest); err != nil {
		no := false
		return &no, err.Error()
	}
	if manifest.ID != applet.ID {
		no := false
		return &no, fmt.Sprintf("manifest declares applet %q, want %q", manifest.ID, applet.ID)
	}
	if manifest.Version == "" {
		no := false
		return &no, "manifest declares no version"
	}
	yes := true
	return &yes, ""
}
