package mcp

import (
	"bufio"
	"bytes"
	"os/exec"
	"regexp"
	"strings"
	"syscall"
	"testing"
	"time"
)

// buildCLI compiles the dagrun binary once for the whole test.
func buildCLI(t *testing.T) string {
	t.Helper()
	bin := t.TempDir() + "/dagrun"
	cmd := exec.Command("go", "build", "-o", bin, "github.com/KooshaPari/dagrun")
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("build: %v\n%s", err, out)
	}
	return bin
}

// readyLineRE is the shape of the line the HTTP transport prints when it is
// ready: the URL a client should use, and how many tools it will find.
var readyLineRE = regexp.MustCompile(`^serving mcp (http://\S+)\s+\(tools (\d+)\)$`)

// TestCLIRefusesANonLoopbackHTTPAddress is the exposure guard at the command
// line, where the operator would actually type it.
//
// A non-loopback address publishes a run directory with no authentication, so
// it is refused with a reason rather than served.
func TestCLIRefusesANonLoopbackHTTPAddress(t *testing.T) {
	bin := buildCLI(t)
	for _, addr := range []string{"0.0.0.0:9999", "192.168.1.10:9999", ":9999"} {
		cmd := exec.Command(bin, "mcp", "--http", addr)
		out, err := cmd.CombinedOutput()
		if err == nil {
			t.Errorf("`dagrun mcp --http %s` exited 0; it must be refused:\n%s", addr, out)
			continue
		}
		if !strings.Contains(string(out), "not loopback") && !strings.Contains(string(out), "no host") {
			t.Errorf("`dagrun mcp --http %s` did not say why it refused:\n%s", addr, out)
		}
	}
}

// TestCLIServesMCPOverHTTPAndStopsCleanly is the end-to-end proof: the
// command prints a ready line a client can use, the client gets the same
// tools over that URL, and SIGTERM stops the server with exit 0.
func TestCLIServesMCPOverHTTPAndStopsCleanly(t *testing.T) {
	bin := buildCLI(t)
	cmd := exec.Command(bin, "mcp", "--http", "127.0.0.1:0")
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		t.Fatal(err)
	}
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	defer func() { _ = cmd.Process.Kill() }()

	reader := bufio.NewReader(stdout)
	line, err := reader.ReadString('\n')
	if err != nil {
		t.Fatalf("no ready line: %v\nstderr: %s", err, stderr.String())
	}
	ready := strings.TrimSpace(line)
	match := readyLineRE.FindStringSubmatch(ready)
	if match == nil {
		t.Fatalf("ready line = %q, want %q", ready, "serving mcp http://HOST:PORT  (tools N)")
	}
	url, count := match[1], match[2]
	if count != "19" {
		t.Errorf("the ready line reports %s tools, want 19", count)
	}

	// A real client handshake against the URL the command published.
	session := httpInitialize(t, url)
	frame, _ := postRPC(t, url, session, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
	result, _ := frame["result"].(map[string]any)
	tools, _ := result["tools"].([]any)
	if len(tools) != len(wantTools) {
		t.Fatalf("the served HTTP transport advertised %d tools, want %d", len(tools), len(wantTools))
	}

	// A normal stop is not a failure.
	if err := cmd.Process.Signal(syscall.SIGTERM); err != nil {
		t.Fatalf("signal: %v", err)
	}
	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("the server exited with %v on SIGTERM; a stop must exit 0\nstderr: %s", err, stderr.String())
		}
	case <-time.After(15 * time.Second):
		t.Fatal("the server did not stop on SIGTERM")
	}
}
