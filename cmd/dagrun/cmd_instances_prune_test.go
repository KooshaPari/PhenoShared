package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/KooshaPari/dagrun/internal/applet"
)

// undeadPID is a pid that no process can hold on any target we build for: macOS
// caps pids at kern.maxproc (99999), Linux defaults to 4194304, and Windows
// allocation never reaches it. Picking a number that merely looks large would
// make the test occasionally decide the opposite of what it asserts.
const undeadPID = 4194305

func seedWithPID(t *testing.T, dir, addr string, pid int) applet.Instance {
	t.Helper()
	inst, err := applet.NewInstance("9.9.9", "/tmp/run-a", addr, nil)
	if err != nil {
		t.Fatalf("NewInstance: %v", err)
	}
	inst.PID = pid
	if _, err := inst.Write(dir); err != nil {
		t.Fatalf("Write: %v", err)
	}
	return inst
}

// What a killed server leaves behind is exactly this: a file whose pid is gone
// and whose URL does not answer. A tray that never pruned showed it forever.
func TestCmdInstancesPrunesDeadAdvertisements(t *testing.T) {
	dir := t.TempDir()
	inst := seedWithPID(t, dir, "127.0.0.1:52399", undeadPID)

	code, out, _, err := runCmd(t, []string{"--dir", dir, "--prune", "--json"})
	if err != nil {
		t.Fatalf("cmdInstances: %v (output %s)", err, out)
	}
	if code != 0 {
		t.Fatalf("exit = %d, want 0", code)
	}
	var body struct {
		Instances []map[string]any `json:"instances"`
		Pruned    []string         `json:"pruned"`
	}
	if err := json.Unmarshal([]byte(out), &body); err != nil {
		t.Fatalf("stdout is not JSON: %v\n%.200q", err, out)
	}
	if len(body.Pruned) != 1 || body.Pruned[0] != inst.ID {
		t.Fatalf("pruned = %v, want [%s]", body.Pruned, inst.ID)
	}
	if len(body.Instances) != 0 {
		t.Errorf("a pruned entry is still listed: %v", body.Instances)
	}

	name, err := inst.FileName()
	if err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(filepath.Join(dir, name)); !os.IsNotExist(err) {
		t.Errorf("registry file survived the prune (stat err = %v)", err)
	}
}

// The conservative half of the rule: an entry whose process is still running is
// kept even when its URL does not answer, because that is what a server looks
// like for the moment between writing its record and serving.
func TestCmdInstancesKeepsUnreachableEntryWithALiveProcess(t *testing.T) {
	dir := t.TempDir()
	seedWithPID(t, dir, "127.0.0.1:52398", os.Getpid())

	_, out, _, err := runCmd(t, []string{"--dir", dir, "--prune", "--json"})
	if err != nil {
		t.Fatalf("cmdInstances: %v", err)
	}
	var body struct {
		Instances []map[string]any `json:"instances"`
		Pruned    []string         `json:"pruned"`
	}
	if err := json.Unmarshal([]byte(out), &body); err != nil {
		t.Fatalf("stdout is not JSON: %v\n%.200q", err, out)
	}
	if len(body.Pruned) != 0 {
		t.Errorf("pruned a live process's entry: %v", body.Pruned)
	}
	if len(body.Instances) != 1 {
		t.Errorf("instances = %d, want the entry kept", len(body.Instances))
	}
}

func TestCmdInstancesKeepsReachableAdvertisement(t *testing.T) {
	dir := t.TempDir()
	ts := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != applet.ContractPath {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"id":"` + applet.ID + `","version":"9.9.9"}`))
	}))
	defer ts.Close()

	inst, err := applet.NewInstance("9.9.9", "/tmp/run-a", strings.TrimPrefix(ts.URL, "http://"), nil)
	if err != nil {
		t.Fatalf("NewInstance: %v", err)
	}
	// The pid is dead on purpose: reachability alone must keep the entry, which
	// is the case where the registry file was written by a supervisor's child and
	// the recorded pid has already been reaped.
	inst.PID = undeadPID
	if _, err := inst.Write(dir); err != nil {
		t.Fatal(err)
	}

	_, out, _, err := runCmd(t, []string{"--dir", dir, "--prune", "--json"})
	if err != nil {
		t.Fatalf("cmdInstances: %v", err)
	}
	var body struct {
		Instances []map[string]any `json:"instances"`
		Pruned    []string         `json:"pruned"`
	}
	if err := json.Unmarshal([]byte(out), &body); err != nil {
		t.Fatalf("stdout is not JSON: %v\n%.200q", err, out)
	}
	if len(body.Pruned) != 0 {
		t.Errorf("pruned a reachable server: %v", body.Pruned)
	}
	if len(body.Instances) != 1 {
		t.Fatalf("instances = %d, want the reachable entry kept", len(body.Instances))
	}
	if reach, ok := body.Instances[0]["reachable"].(bool); !ok || !reach {
		t.Errorf("reachable = %v, want true", body.Instances[0]["reachable"])
	}
}

// Without the flag nothing is deleted. A read-only listing is what most callers
// want, and a listing that quietly deleted files would be a nasty surprise for
// one that ran it to inspect a problem.
func TestCmdInstancesDoesNotPruneByDefault(t *testing.T) {
	dir := t.TempDir()
	inst := seedWithPID(t, dir, "127.0.0.1:52397", undeadPID)
	name, err := inst.FileName()
	if err != nil {
		t.Fatal(err)
	}

	if _, _, _, err := runCmd(t, []string{"--dir", dir}); err != nil {
		t.Fatalf("cmdInstances: %v", err)
	}
	if _, err := os.Stat(filepath.Join(dir, name)); err != nil {
		t.Fatalf("a plain listing deleted a record: %v", err)
	}
	if applet.ProcessAlive(undeadPID) {
		// Guard the guard: the fixture pid must really be dead, or the prune tests
		// above would pass for the wrong reason.
		t.Fatalf("fixture pid %d is alive on this host; the dead-pid premise is void", undeadPID)
	}
}

// runCmd captures both streams for a command that takes its own flags.
func runCmd(t *testing.T, args []string) (int, string, string, error) {
	t.Helper()
	out, errOut, err := captureStdoutStderr(t, func() error { return cmdInstances(args) })
	code := 0
	if err != nil {
		code = 1
	}
	return code, out, errOut, err
}

// The Windows hazard unicorn measured: a recycled pid points at some unrelated
// live process, so "the pid is in use" alone kept a record forever even though
// nothing answered on its port. Age is the second signal.
func TestPrunableAgesOutARecycledPID(t *testing.T) {
	inst := applet.Instance{PID: os.Getpid(), StartedAt: "2026-01-01T00:00:00Z"}
	if !prunable(inst, time.Date(2026, 1, 1, 1, 0, 0, 0, time.UTC)) {
		t.Fatalf("an unreachable record an hour old survived a live-but-unrelated pid")
	}
}

func TestPrunableKeepsAServerStillStarting(t *testing.T) {
	now := time.Now().UTC()
	inst := applet.Instance{PID: os.Getpid(), StartedAt: now.Format(time.RFC3339)}
	if prunable(inst, now) {
		t.Fatalf("a record written seconds ago was pruned; a starting server advertises before it serves")
	}
}

func TestPrunableKeepsAnUnreadableStartTime(t *testing.T) {
	inst := applet.Instance{PID: os.Getpid(), StartedAt: "not a timestamp"}
	if prunable(inst, time.Now().UTC().Add(time.Hour*24*365)) {
		t.Fatalf("an unreadable start time was read as an old one")
	}
}

func TestPrunableTrustsADeadPIDRegardlessOfAge(t *testing.T) {
	now := time.Now().UTC()
	inst := applet.Instance{PID: undeadPID, StartedAt: now.Format(time.RFC3339)}
	if !prunable(inst, now) {
		t.Fatalf("a dead pid was kept just because its record was young")
	}
}

// When the only record is prunable, one run printed both "no dagrun servers
// advertised" and "pruned stale advertisement": the listing rendered the
// post-prune remainder while the prose claimed nothing had been advertised.
func TestCmdInstancesPruneProseDoesNotContradictItself(t *testing.T) {
	dir := t.TempDir()
	seedWithPID(t, dir, "127.0.0.1:52396", undeadPID)

	_, out, _, err := runCmd(t, []string{"--dir", dir, "--prune"})
	if err != nil {
		t.Fatalf("cmdInstances: %v", err)
	}
	if strings.Contains(out, "no dagrun servers advertised") {
		t.Errorf("prose claims nothing was advertised after pruning something:\n%s", out)
	}
	if !strings.Contains(out, "pruned stale advertisement") {
		t.Errorf("the pruned entry was not reported:\n%s", out)
	}
	if !strings.Contains(out, "no dagrun servers remain") {
		t.Errorf("prose does not say the registry is now empty:\n%s", out)
	}
}

func TestCmdInstancesEmptyRegistryProseStillReadsPlainly(t *testing.T) {
	dir := t.TempDir()
	_, out, _, err := runCmd(t, []string{"--dir", dir, "--prune"})
	if err != nil {
		t.Fatalf("cmdInstances: %v", err)
	}
	if !strings.Contains(out, "no dagrun servers advertised") {
		t.Errorf("an empty registry with nothing pruned should say so:\n%s", out)
	}
}
