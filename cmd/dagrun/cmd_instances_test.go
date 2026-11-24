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

// One concept had two JSON names: `serve --check --json` reports instance_dir,
// `instances --json` reported dir. A launcher written against one decoded the
// other as an empty string and reported "no servers found" instead of failing,
// which is the worst shape of bug: no error, wrong answer.
func TestCmdInstancesJSONNamesTheRegistryBothWays(t *testing.T) {
	dir := t.TempDir()
	seedWithPID(t, dir, "127.0.0.1:52395", undeadPID)

	_, out, _, err := runCmd(t, []string{"--dir", dir, "--json"})
	if err != nil {
		t.Fatalf("cmdInstances: %v", err)
	}
	var body struct {
		Dir         string `json:"dir"`
		InstanceDir string `json:"instance_dir"`
	}
	if err := json.Unmarshal([]byte(out), &body); err != nil {
		t.Fatalf("stdout is not JSON: %v\n%.200q", err, out)
	}
	if body.Dir != dir {
		t.Errorf("dir = %q, want %q", body.Dir, dir)
	}
	if body.InstanceDir != body.Dir {
		t.Errorf("instance_dir = %q, dir = %q; the same value must appear under both names", body.InstanceDir, body.Dir)
	}
}
