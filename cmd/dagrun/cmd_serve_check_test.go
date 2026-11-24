package main

import (
	"encoding/json"
	"net"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/KooshaPari/dagrun/internal/applet"
)

// The failure that motivated --check: a server started in a directory with no
// plan exits without binding, so every request against it is connection-refused
// and a caller reads that as a broken server rather than a missing precondition.
func TestServeCheckReportsMissingPlanInsteadOfSilence(t *testing.T) {
	dir := t.TempDir()
	code, stdout, stderr := runServeCheck(t, dir)
	if code == 0 {
		t.Fatalf("exit = 0, want non-zero for a directory with no plan; stderr=%s", stderr)
	}
	var rep map[string]any
	if err := json.Unmarshal([]byte(stdout), &rep); err != nil {
		t.Fatalf("stdout is not JSON: %v\n%.120q", err, stdout)
	}
	if rep["ok"] != false {
		t.Errorf("ok = %v, want false", rep["ok"])
	}
	msg, _ := rep["error"].(string)
	if !strings.Contains(msg, "no plan installed") {
		t.Errorf("error = %q, want it to name the missing plan", msg)
	}
	if !strings.Contains(msg, "dagrun plan") {
		t.Errorf("error = %q, want it to name the fixing command", msg)
	}
	// Absent fields rather than empty ones: "no address" and "address 0.0.0.0:0"
	// must not look alike to a parser.
	if _, present := rep["servable_url"]; present {
		t.Errorf("servable_url present on a failure: %v", rep["servable_url"])
	}
}

func TestServeCheckReportsServableDirectoryWithARealPort(t *testing.T) {
	dir := plannedDir(t)
	code, stdout, stderr := runServeCheck(t, dir)
	if code != 0 {
		t.Fatalf("exit = %d, want 0; stdout=%s stderr=%s", code, stdout, stderr)
	}
	var rep map[string]any
	if err := json.Unmarshal([]byte(stdout), &rep); err != nil {
		t.Fatalf("stdout is not JSON: %v\n%.120q", err, stdout)
	}
	if rep["ok"] != true {
		t.Fatalf("ok = %v, want true; report=%v", rep["ok"], rep)
	}
	url, _ := rep["servable_url"].(string)
	if !strings.HasPrefix(url, "http://127.0.0.1:") {
		t.Errorf("servable_url = %q, want a loopback URL", url)
	}
	if rep["plan"] == "" || rep["plan"] == nil {
		t.Errorf("plan missing from a success report: %v", rep)
	}
	if _, present := rep["error"]; present {
		t.Errorf("error present on success: %v", rep["error"])
	}
}

// The preflight must not leave a listener behind. Two runs in a row prove the
// port was released rather than held: if Close did nothing, the second bind on
// the same fixed address would fail, and a launcher polling every few seconds
// would accumulate leaked ports.
func TestServeCheckReleasesItsPort(t *testing.T) {
	dir := plannedDir(t)

	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := ln.Addr().String()
	if err := ln.Close(); err != nil {
		t.Fatal(err)
	}

	for i := 0; i < 2; i++ {
		code, stdout, stderr := runServeCheck(t, dir, "--addr", addr)
		if code != 0 {
			t.Fatalf("run %d: exit = %d, want 0; stdout=%s stderr=%s", i, code, stdout, stderr)
		}
		var rep map[string]any
		if err := json.Unmarshal([]byte(stdout), &rep); err != nil {
			t.Fatalf("run %d: not JSON: %v", i, err)
		}
		if got, _ := rep["addr"].(string); got != addr {
			t.Errorf("run %d: addr = %q, want the requested %q", i, got, addr)
		}
	}
}

// A port already taken is the other way a launcher's start fails, and the
// preflight is the only place that can say so before the tray shows an error.
func TestServeCheckReportsATakenPort(t *testing.T) {
	dir := plannedDir(t)
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer func() { _ = ln.Close() }()

	code, stdout, stderr := runServeCheck(t, dir, "--addr", ln.Addr().String())
	if code == 0 {
		t.Fatalf("exit = 0 with the port held; stdout=%s stderr=%s", stdout, stderr)
	}
	var rep map[string]any
	if err := json.Unmarshal([]byte(stdout), &rep); err != nil {
		t.Fatalf("not JSON: %v", err)
	}
	if rep["ok"] != false {
		t.Errorf("ok = %v, want false", rep["ok"])
	}
	if msg, _ := rep["error"].(string); !strings.Contains(msg, "cannot listen") {
		t.Errorf("error = %q, want it to say the address is unusable", msg)
	}
}

// Prose mode is for a human running it by hand: a success is one readable line
// on stdout, and a failure is said exactly once, by main's error path. Both
// halves are asserted because the earlier version printed the failure twice.
func TestServeCheckProseModeSaysTheFailureOnce(t *testing.T) {
	dir := t.TempDir()
	code, stdout, _ := runServeCheck(t, dir, "--no-json")
	if code == 0 {
		t.Fatal("exit = 0, want non-zero")
	}
	if strings.TrimSpace(stdout) != "" {
		t.Errorf("prose failure wrote to stdout: %.80q; main owns that message", stdout)
	}

	okDir := plannedDir(t)
	code, stdout, _ = runServeCheck(t, okDir, "--no-json")
	if code != 0 {
		t.Fatalf("exit = %d on a servable dir, want 0", code)
	}
	if lines := strings.Count(strings.TrimSpace(stdout), "\n"); lines != 0 {
		t.Errorf("servable report is %d lines, want 1: %.120q", lines+1, stdout)
	}
	if !strings.HasPrefix(strings.TrimSpace(stdout), "servable http://127.0.0.1:") {
		t.Errorf("prose = %.100q, want it to lead with the URL", stdout)
	}
}

// A preflight must not advertise. Bind advertises, and the retraction that pairs
// with it happens when Listen returns, which a preflight never reaches, so an
// advertising preflight would leave a record for a server that is not there.
// Measured before the fix: every poll added one phantom entry to the real
// registry, which is exactly the tray confusion the registry exists to prevent.
func TestServeCheckLeavesNoAdvertisement(t *testing.T) {
	registry := t.TempDir()
	t.Setenv(applet.InstanceDirEnv, registry)
	dir := plannedDir(t)

	code, stdout, stderr := runServeCheck(t, dir)
	if code != 0 {
		t.Fatalf("exit = %d, want 0; stdout=%s stderr=%s", code, stdout, stderr)
	}
	var rep map[string]any
	if err := json.Unmarshal([]byte(stdout), &rep); err != nil {
		t.Fatalf("not JSON: %v", err)
	}
	// The report still names the registry, so a caller can see where a real start
	// would advertise. Naming it is not the same as writing to it.
	if got, _ := rep["instance_dir"].(string); got != registry {
		t.Errorf("instance_dir = %q, want the resolved %q", got, registry)
	}
	// `dir` means the run directory here and the registry in `dagrun instances
	// --json`, so the unambiguous names are pinned: a consumer that reads
	// run_dir or instance_dir gets the right value from either command.
	if got, _ := rep["run_dir"].(string); got != dir {
		t.Errorf("run_dir = %q, want the run directory %q", got, dir)
	}
	if got, _ := rep["dir"].(string); got != dir {
		t.Errorf("dir = %q, want the run directory %q", got, dir)
	}
	entries, err := os.ReadDir(registry)
	if err != nil {
		t.Fatalf("registry dir: %v", err)
	}
	if len(entries) != 0 {
		names := make([]string, 0, len(entries))
		for _, e := range entries {
			names = append(names, e.Name())
		}
		t.Fatalf("preflight wrote %d registry entries: %v", len(entries), names)
	}
}

// runServeCheck invokes the serve command's preflight through the real entry
// path, so the flag wiring is covered rather than the helper alone. `--no-json`
// is stripped and used to mean "prose mode": flagSet registers --json as a bool
// defaulting to false, so prose is the default and --no-json must not reach it.
func runServeCheck(t *testing.T, dir string, extra ...string) (int, string, string) {
	t.Helper()
	args := []string{"--dir", dir, "--check"}
	jsonMode := true
	for _, a := range extra {
		if a == "--no-json" {
			jsonMode = false
			continue
		}
		args = append(args, a)
	}
	if jsonMode {
		args = append(args, "--json")
	}
	stdout, stderr, err := captureStdoutStderr(t, func() error { return cmdServe(args) })
	code := 0
	if err != nil {
		code = 1
	}
	return code, stdout, stderr
}

// captureStdoutStderr runs fn with both streams redirected and returns what each
// wrote. Both are captured because the command splits its report (stdout, the
// machine answer) from any error (stderr), and a test that looked at only one
// could not see a report that went to the wrong stream.
func captureStdoutStderr(t *testing.T, fn func() error) (string, string, error) {
	t.Helper()
	outR, outW, err := os.Pipe()
	if err != nil {
		t.Fatalf("pipe: %v", err)
	}
	errR, errW, err := os.Pipe()
	if err != nil {
		t.Fatalf("pipe: %v", err)
	}
	oldOut, oldErr := os.Stdout, os.Stderr
	os.Stdout, os.Stderr = outW, errW
	outCh, errCh := make(chan string, 1), make(chan string, 1)
	go func() { outCh <- drain(outR) }()
	go func() { errCh <- drain(errR) }()

	runErr := fn()

	_ = outW.Close()
	_ = errW.Close()
	os.Stdout, os.Stderr = oldOut, oldErr
	return <-outCh, <-errCh, runErr
}

func drain(r *os.File) string {
	var sb strings.Builder
	buf := make([]byte, 4096)
	for {
		n, err := r.Read(buf)
		sb.Write(buf[:n])
		if err != nil {
			return sb.String()
		}
	}
}

// plannedDir builds a directory with an installed plan, using the same command a
// person would run, so the fixture cannot drift from the real layout.
func plannedDir(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	spec := filepath.Join(t.TempDir(), "plan.yaml")
	body := `version: 1
run: preflight
nodes:
  - id: "1"
    kind: INTENT
    role: intent
    title: freeze scope
    artifacts: [{path: a.md, min_bytes: 1}]
`
	if err := os.WriteFile(spec, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, _, err := captureStdoutStderr(t, func() error { return cmdPlan([]string{"--dir", dir, spec}) }); err != nil {
		t.Fatalf("plan install failed: %v", err)
	}
	return dir
}
