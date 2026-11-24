package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/KooshaPari/dagrun/internal/applet"
)

// seedInstance writes one advertisement into dir. By default there is no server
// behind it, which is exactly the state a killed process leaves.
func seedInstance(t *testing.T, dir, startedAt, addr string) applet.Instance {
	t.Helper()
	inst, err := applet.NewInstance("9.9.9", "/tmp/run-a", addr, nil)
	if err != nil {
		t.Fatalf("NewInstance: %v", err)
	}
	inst.StartedAt = startedAt
	if _, err := inst.Write(dir); err != nil {
		t.Fatalf("Write: %v", err)
	}
	return inst
}

// `dagrun instances` is what a tray icon or a launcher calls: it must find a
// server it did not start, and it must say "advertised" rather than "alive"
// when it has not contacted anything.
func TestCmdInstancesListsWithoutVerifying(t *testing.T) {
	dir := t.TempDir()
	seedInstance(t, dir, "2026-11-24T00:00:00Z", "127.0.0.1:52341")

	out := captureStdout(t, func() {
		if err := cmdInstances([]string{"--dir", dir}); err != nil {
			t.Fatalf("cmdInstances: %v", err)
		}
	})
	if !strings.Contains(out, "127.0.0.1:52341") {
		t.Fatalf("origin is missing from the listing:\n%s", out)
	}
	if !strings.Contains(out, "advertised") {
		t.Fatalf("an unverified entry must say advertised, not imply liveness:\n%s", out)
	}
	for _, want := range []string{"ID", "VERSION", "ORIGIN", "STARTED", "STATUS"} {
		if !strings.Contains(out, want) {
			t.Fatalf("column %q is missing from the listing:\n%s", want, out)
		}
	}
}

func TestCmdInstancesEmptyRegistryIsNotAnError(t *testing.T) {
	var err error
	out := captureStdout(t, func() {
		err = cmdInstances([]string{"--dir", filepath.Join(t.TempDir(), "none")})
	})
	if err != nil {
		t.Fatalf("an empty registry is not a failure: %v", err)
	}
	if !strings.Contains(out, "no dagrun servers") {
		t.Fatalf("empty listing did not say so:\n%s", out)
	}
}

// The whole point of --verify is to separate "a file exists" from "a server
// answers", because a killed server leaves its file behind.
func TestCmdInstancesVerifySeparatesDeadFromAlive(t *testing.T) {
	live := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != applet.ContractPath {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"` + applet.ID + `","version":"9.9.9"}`))
	}))
	defer live.Close()

	dir := t.TempDir()
	seedInstance(t, dir, "2026-11-24T00:00:00Z", live.Listener.Addr().String())
	dead := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}))
	deadAddr := dead.Listener.Addr().String()
	dead.Close() // nothing is listening on that port any more
	seedInstance(t, dir, "2026-11-24T00:00:01Z", deadAddr)

	var err error
	out := captureStdout(t, func() {
		err = cmdInstances([]string{"--dir", dir, "--verify", "--json"})
	})
	if err != nil {
		t.Fatalf("cmdInstances: %v", err)
	}

	var body struct {
		Instances []struct {
			Origin    string `json:"origin"`
			Reachable *bool  `json:"reachable"`
			Error     string `json:"error"`
		} `json:"instances"`
		Errors []string `json:"errors"`
	}
	if err := json.Unmarshal([]byte(out), &body); err != nil {
		t.Fatalf("output is not JSON: %v\n%s", err, out)
	}
	if len(body.Instances) != 2 {
		t.Fatalf("got %d instances, want 2:\n%s", len(body.Instances), out)
	}
	for _, inst := range body.Instances {
		if inst.Reachable == nil {
			t.Fatalf("--verify left %s unchecked", inst.Origin)
		}
		wantReachable := strings.Contains(inst.Origin, live.Listener.Addr().String())
		if *inst.Reachable != wantReachable {
			t.Fatalf("%s reachable = %v, want %v (error %q)", inst.Origin, *inst.Reachable, wantReachable, inst.Error)
		}
		if !wantReachable && inst.Error == "" {
			t.Fatalf("%s was reported unreachable with no reason", inst.Origin)
		}
	}
}

func TestCmdInstancesVerifyRejectsAForeignManifest(t *testing.T) {
	// A loopback port serving something that is not dagrun must not be reported
	// as a dagrun server just because a file says so.
	impostor := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = w.Write([]byte(`{"id":"someone-else","version":"1"}`))
	}))
	defer impostor.Close()
	dir := t.TempDir()
	seedInstance(t, dir, "2026-11-24T00:00:00Z", impostor.Listener.Addr().String())

	var err error
	out := captureStdout(t, func() {
		err = cmdInstances([]string{"--dir", dir, "--verify", "--json"})
	})
	if err != nil {
		t.Fatalf("cmdInstances: %v", err)
	}
	var body struct {
		Instances []struct {
			Reachable *bool  `json:"reachable"`
			Error     string `json:"error"`
		} `json:"instances"`
	}
	if err := json.Unmarshal([]byte(out), &body); err != nil {
		t.Fatalf("output is not JSON: %v\n%s", err, out)
	}
	if len(body.Instances) != 1 || body.Instances[0].Reachable == nil || *body.Instances[0].Reachable {
		t.Fatalf("an impostor manifest was accepted:\n%s", out)
	}
	if !strings.Contains(body.Instances[0].Error, "applet") {
		t.Fatalf("error does not name the contract mismatch: %q", body.Instances[0].Error)
	}
}

func TestCmdInstancesReportsUnreadableEntriesWithoutHidingGoodOnes(t *testing.T) {
	dir := t.TempDir()
	seedInstance(t, dir, "2026-11-24T00:00:00Z", "127.0.0.1:52341")
	if err := os.WriteFile(filepath.Join(dir, "broken.json"), []byte("{"), 0o600); err != nil {
		t.Fatalf("seed: %v", err)
	}

	var err error
	out := captureStdout(t, func() {
		err = cmdInstances([]string{"--dir", dir, "--json"})
	})
	if err != nil {
		t.Fatalf("one bad file must not fail the command: %v", err)
	}
	var body struct {
		Instances []struct {
			Origin string `json:"origin"`
		} `json:"instances"`
		Errors []string `json:"errors"`
	}
	if err := json.Unmarshal([]byte(out), &body); err != nil {
		t.Fatalf("output is not JSON: %v\n%s", err, out)
	}
	if len(body.Instances) != 1 {
		t.Fatalf("the good entry was dropped:\n%s", out)
	}
	if len(body.Errors) != 1 || !strings.Contains(body.Errors[0], "broken.json") {
		t.Fatalf("the unreadable entry was not reported in errors: %v", body.Errors)
	}
}

func TestCmdInstancesHelpExitsClean(t *testing.T) {
	out := captureStdout(t, func() {
		if err := cmdInstances([]string{"--help"}); err != nil {
			t.Fatalf("--help is not a failure: %v", err)
		}
	})
	if !strings.Contains(out, "dagrun instances") {
		t.Fatalf("help text does not name the command:\n%s", out)
	}
	if !strings.Contains(out, "hint") {
		t.Fatalf("help text must warn that the registry is a hint:\n%s", out)
	}
}

// A launcher cannot construct the registry path: it is <config>/dagrun/instances,
// which is ~/.config on Linux, ~/Library/Application Support on macOS and
// %APPDATA% on Windows. `instance_dir` in the JSON is the only supported way to
// learn it, and it must be the same key `serve --check --json` uses for the same
// value, so one reader works against both commands.
func TestCmdInstancesJSONReportsInstanceDir(t *testing.T) {
	var body struct {
		InstanceDir string           `json:"instance_dir"`
		Instances   []map[string]any `json:"instances"`
		Errors      []string         `json:"errors"`
	}

	// Explicit directory.
	explicit := t.TempDir()
	seedInstance(t, explicit, "2026-11-24T00:00:00Z", "127.0.0.1:52341")
	out := captureStdout(t, func() {
		if err := cmdInstances([]string{"--dir", explicit, "--json"}); err != nil {
			t.Fatalf("cmdInstances: %v", err)
		}
	})
	if err := json.Unmarshal([]byte(out), &body); err != nil {
		t.Fatalf("output is not JSON: %v\n%s", err, out)
	}
	if body.InstanceDir != explicit {
		t.Errorf("instance_dir = %q, want the explicit %q", body.InstanceDir, explicit)
	}
	if len(body.Instances) != 1 {
		t.Errorf("instance_dir reporting disturbed the listing: %d entries", len(body.Instances))
	}

	// Per-platform default, via the override the server itself honours.
	override := filepath.Join(t.TempDir(), "elsewhere")
	t.Setenv(applet.InstanceDirEnv, override)
	out = captureStdout(t, func() {
		if err := cmdInstances([]string{"--json"}); err != nil {
			t.Fatalf("cmdInstances: %v", err)
		}
	})
	if err := json.Unmarshal([]byte(out), &body); err != nil {
		t.Fatalf("output is not JSON: %v\n%s", err, out)
	}
	if body.InstanceDir != override {
		t.Errorf("instance_dir = %q, want the override %q", body.InstanceDir, override)
	}

	// Resolution with no override must agree with the resolver the server uses,
	// never a path this command invented.
	t.Setenv(applet.InstanceDirEnv, "")
	want, err := applet.DefaultInstanceDir()
	if err != nil {
		t.Fatalf("DefaultInstanceDir: %v", err)
	}
	out = captureStdout(t, func() {
		if err := cmdInstances([]string{"--json"}); err != nil {
			t.Fatalf("cmdInstances: %v", err)
		}
	})
	if err := json.Unmarshal([]byte(out), &body); err != nil {
		t.Fatalf("output is not JSON: %v\n%s", err, out)
	}
	if body.InstanceDir != want {
		t.Errorf("instance_dir = %q, want the resolved %q", body.InstanceDir, want)
	}

	// The retired key must not come back as a silent alias: one concept, one name.
	var keys map[string]json.RawMessage
	if err := json.Unmarshal([]byte(out), &keys); err != nil {
		t.Fatalf("output is not an object: %v", err)
	}
	if _, ok := keys["dir"]; ok {
		t.Errorf("instance_dir was added alongside a legacy dir key:\n%s", out)
	}
}

// Listing is read-only. A host polls this command on a timer, so a poll that
// rewrote, retracted or added an advertisement would make the launcher the thing
// that breaks discovery.
func TestCmdInstancesJSONLeavesTheRegistryUntouched(t *testing.T) {
	dir := t.TempDir()
	seedInstance(t, dir, "2026-11-24T00:00:00Z", "127.0.0.1:52341")
	seedInstance(t, dir, "2026-11-24T00:00:02Z", "127.0.0.1:52342")

	snapshot := func() map[string]string {
		entries, err := os.ReadDir(dir)
		if err != nil {
			t.Fatalf("ReadDir: %v", err)
		}
		got := make(map[string]string, len(entries))
		for _, e := range entries {
			body, err := os.ReadFile(filepath.Join(dir, e.Name()))
			if err != nil {
				t.Fatalf("ReadFile %s: %v", e.Name(), err)
			}
			got[e.Name()] = string(body)
		}
		return got
	}

	before := snapshot()
	for _, args := range [][]string{
		{"--dir", dir},
		{"--dir", dir, "--json"},
		{"--dir", dir, "--verify"},
	} {
		captureStdout(t, func() {
			if err := cmdInstances(args); err != nil {
				t.Fatalf("cmdInstances %v: %v", args, err)
			}
		})
	}
	after := snapshot()

	if len(before) != len(after) {
		t.Fatalf("listing changed the registry: %d files before, %d after", len(before), len(after))
	}
	for name, body := range before {
		if after[name] != body {
			t.Errorf("listing rewrote %s", name)
		}
	}
}
