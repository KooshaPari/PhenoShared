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

const instancesHelp = `usage: dagrun instances [--dir REGISTRY] [--verify] [--prune] [--json]

List running dagrun servers that advertise themselves on this machine.

A server started by ` + "`dagrun serve`" + ` records its URLs in a small file under the
instance directory (default ` + "`$DAGRUN_INSTANCE_DIR`" + `, else <config>/dagrun/instances).
This command reads that directory, which is what a tray icon, a menu bar item or
a master console uses to find a server it did not start.

  --dir DIR   registry directory (default: the instance directory)
  --verify    fetch each manifest to confirm the server is actually alive
  --prune     delete advertisements that are unreachable and either from a dead
              process or unreachable for longer than any startup takes, then
              report what was removed. Implies --verify, because deleting an
              entry that was never contacted would be a guess.
  --json      print the entries as JSON; the registry path appears as both
              "dir" and "instance_dir" (the field ` + "`dagrun serve --check --json`" + `
              uses for the same value)

The registry is a hint. A killed server leaves its file behind, so an entry
without --verify says "advertised", not "reachable".

A tray icon wants --verify on every poll and --prune on a slow one, otherwise a
killed server stays on the menu until the file is deleted by hand. Pruning is
deliberately conservative: an entry survives if its manifest answers, or its pid
is still running and its record is younger than ten minutes.`

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
	prune := fs.Bool("prune", false, "delete advertisements that are unreachable and from a dead process")
	jsonOut := fs.Bool("json", false, "machine-readable JSON on stdout")
	if err := fs.Parse(args); err != nil {
		return err
	}
	// Pruning decides by reachability, so it cannot run without the check. It is
	// implied rather than refused: a caller asking to prune is asking for the
	// check too, and refusing only makes it a two-flag incantation to remember.
	if *prune {
		*verify = true
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
	var pruned []string
	var pruneErrs []string
	for _, inst := range instances {
		rep := instanceReport{Instance: inst}
		if *verify {
			rep.Reachable, rep.Error = probeManifest(inst)
		}
		if *prune && rep.Reachable != nil && !*rep.Reachable && pruneAllowed(applet.ProcessLiveness(inst.PID)) {
			name, err := inst.FileName()
			if err != nil {
				pruneErrs = append(pruneErrs, err.Error())
			} else if err := applet.RemoveInstance(where, name); err != nil {
				pruneErrs = append(pruneErrs, err.Error())
			} else {
				pruned = append(pruned, inst.ID)
				continue
			}
		}
		reports = append(reports, rep)
	}

	if *jsonOut {
		// Errors are part of the answer, not a side channel: a caller that saw
		// only the valid entries would believe a corrupt registry is empty.
		body := struct {
			Dir string `json:"dir"`
			// InstanceDir carries the same value as Dir. The registry is one
			// concept and it had two names: `serve --check --json` reported
			// instance_dir while this command reported dir, so a launcher
			// written against one silently decoded the other as empty and
			// concluded "no servers" rather than failing. Both are emitted;
			// neither is deprecated.
			InstanceDir string           `json:"instance_dir"`
			Instances   []instanceReport `json:"instances"`
			Errors      []string         `json:"errors"`
			Pruned      []string         `json:"pruned"`
			PruneErrs   []string         `json:"prune_errors"`
		}{Dir: where, InstanceDir: where, Instances: reports, Errors: []string{}, Pruned: []string{}, PruneErrs: []string{}}
		for _, err := range errs {
			body.Errors = append(body.Errors, err.Error())
		}
		body.Pruned = append(body.Pruned, pruned...)
		body.PruneErrs = append(body.PruneErrs, pruneErrs...)
		out, err := json.MarshalIndent(body, "", "  ")
		if err != nil {
			return err
		}
		fmt.Fprintf(os.Stdout, "%s\n", out)
		return nil
	}

	if len(reports) == 0 {
		if len(pruned) == 0 {
			fmt.Fprintf(os.Stdout, "no dagrun servers advertised in %s\n", where)
		} else {
			// Saying "nothing is advertised" after deleting the only entry
			// reads as if the deletion and the emptiness were unrelated
			// facts. They are the same fact.
			fmt.Fprintf(os.Stdout, "no dagrun servers remain in %s after pruning\n", where)
		}
	} else {
		printInstances(reports)
	}
	// A bad file is reported and does not fail the command: the good entries are
	// still the answer, and a launcher must not treat one stale file as "no
	// server at all".
	for _, err := range errs {
		fmt.Fprintf(os.Stderr, "dagrun instances: skipping unreadable entry: %v\n", err)
	}
	for _, id := range pruned {
		fmt.Fprintf(os.Stdout, "pruned stale advertisement %s\n", id)
	}
	for _, err := range pruneErrs {
		fmt.Fprintf(os.Stderr, "dagrun instances: could not prune: %v\n", err)
	}
	return nil
}

// pruneAllowed reports whether a failed liveness probe authorises deleting an
// advertisement whose endpoint has already been confirmed unreachable.
//
// Only proven death qualifies. Both other states retain the record:
//
//	unknown - the probe could not ask (ERROR_ACCESS_DENIED, EPERM, or an
//	          unreadable exit code). A pid you cannot ask about is not a pid
//	          that is gone; measured cost of treating it as gone was deleting
//	          the advertisement of live pid 4 on the desk.
//	alive   - a running process holds the pid. It may be the server, or it may
//	          be an unrelated process that inherited the number. Distinguishing
//	          those needs process identity (start time, image path) that the
//	          record does not carry, so a recycled pid keeps its record until
//	          that identity check exists.
//
// Age deliberately plays no part. It used to: an unreachable record older than
// ten minutes was deleted even when its pid was alive, on the reasoning that a
// genuine server advertises seconds before it serves (observed with pid 45964,
// gone from the task list, port refusing). The consequence of removing it is
// accepted and stated: a recycled pid whose record never proves dead now
// survives indefinitely. A record nobody reads is cheaper than deleting one a
// running server still depends on, and age is evidence about a file, not about
// a process.
func pruneAllowed(l applet.Liveness) bool {
	return l == applet.LivenessDead
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
