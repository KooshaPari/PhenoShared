package mcp

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"sort"
	"strings"
	"testing"
	"time"

	sdkmcp "github.com/modelcontextprotocol/go-sdk/mcp"
)

// httpTestServer starts the HTTP transport on a real loopback listener.
func httpTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	ts := httptest.NewServer(New(Config{Version: "test"}).HTTPHandler())
	t.Cleanup(ts.Close)
	return ts
}

// postRPC sends one JSON-RPC message and returns the reply plus the headers.
//
// The headers matter: the Streamable HTTP transport hands out a session id on
// initialize and expects it back on every later request.
func postRPC(t *testing.T, url, sessionID, body string) (map[string]any, http.Header) {
	t.Helper()
	req, err := http.NewRequest(http.MethodPost, url, strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json, text/event-stream")
	if sessionID != "" {
		req.Header.Set("Mcp-Session-Id", sessionID)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("post %s: %v", body, err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != http.StatusOK {
		t.Fatalf("post %s: status %d\n%s", body, resp.StatusCode, raw)
	}
	return parseRPCFrame(t, raw), resp.Header
}

// postNotification sends a notification, which by the protocol is not answered.
func postNotification(t *testing.T, url, sessionID, body string) {
	t.Helper()
	req, err := http.NewRequest(http.MethodPost, url, strings.NewReader(body))
	if err != nil {
		t.Fatal(err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json, text/event-stream")
	if sessionID != "" {
		req.Header.Set("Mcp-Session-Id", sessionID)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("post %s: %v", body, err)
	}
	defer resp.Body.Close()
	_, _ = io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusAccepted && resp.StatusCode != http.StatusOK {
		t.Fatalf("notification %s: status %d", body, resp.StatusCode)
	}
}

// parseRPCFrame pulls the JSON-RPC message out of a reply.
//
// The Streamable HTTP transport answers a request-carrying POST with one
// server-sent event whose data line holds the message. A JSON body is
// accepted too, because the transport can be asked for one.
func parseRPCFrame(t *testing.T, raw []byte) map[string]any {
	t.Helper()
	text := string(raw)
	if strings.Contains(text, "data:") {
		for _, line := range strings.Split(text, "\n") {
			line = strings.TrimSpace(line)
			if !strings.HasPrefix(line, "data:") {
				continue
			}
			payload := strings.TrimSpace(strings.TrimPrefix(line, "data:"))
			var m map[string]any
			if err := json.Unmarshal([]byte(payload), &m); err != nil {
				t.Fatalf("SSE data is not JSON: %v\n%s", err, payload)
			}
			return m
		}
		t.Fatalf("no data frame in the reply:\n%s", text)
	}
	var m map[string]any
	if err := json.Unmarshal(raw, &m); err != nil {
		t.Fatalf("reply is not JSON: %v\n%s", err, text)
	}
	return m
}

// httpToolNames returns the tool names a client sees over HTTP.
func httpToolNames(t *testing.T, url string) []string {
	t.Helper()
	session := httpInitialize(t, url)
	frame, _ := postRPC(t, url, session, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
	result, _ := frame["result"].(map[string]any)
	if result == nil {
		t.Fatalf("tools/list returned no result: %v", frame)
	}
	rawTools, _ := result["tools"].([]any)
	names := make([]string, 0, len(rawTools))
	for _, raw := range rawTools {
		m, _ := raw.(map[string]any)
		name, _ := m["name"].(string)
		names = append(names, name)
	}
	return names
}

// httpInitialize performs the handshake and returns the session id.
func httpInitialize(t *testing.T, url string) string {
	t.Helper()
	frame, hdr := postRPC(t, url, "", `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}`)
	result, _ := frame["result"].(map[string]any)
	if result == nil {
		t.Fatalf("initialize returned no result: %v", frame)
	}
	info, _ := result["serverInfo"].(map[string]any)
	if info["name"] != "dagrun" {
		t.Errorf("serverInfo.name = %v, want dagrun", info["name"])
	}
	session := hdr.Get("Mcp-Session-Id")
	if session == "" {
		t.Fatal("initialize returned no Mcp-Session-Id header")
	}
	postNotification(t, url, session, `{"jsonrpc":"2.0","method":"notifications/initialized"}`)
	return session
}

// TestHTTPInitializeAndToolsList proves the HTTP transport answers the two
// calls every MCP client makes first.
//
// The order is compared as a set, not as a sequence: the SDK serves its tools
// sorted by name, while the stdio transport serves them in catalogue order.
// The set is the contract; the order is the SDK's business.
func TestHTTPInitializeAndToolsList(t *testing.T) {
	ts := httpTestServer(t)
	names := httpToolNames(t, ts.URL)
	if len(names) != len(wantTools) {
		t.Fatalf("HTTP advertised %d tools, want %d", len(names), len(wantTools))
	}
	got := sortedNames(names)
	want := sortedNames(wantTools)
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("HTTP tools %v, want %v", got, want)
		}
	}
}

// sortedNames returns a sorted copy, so two lists can be compared as sets.
func sortedNames(in []string) []string {
	out := append([]string(nil), in...)
	sort.Strings(out)
	return out
}

// TestHTTPToolSetIsIdenticalToTheStdioToolSet is the anti-duplication test.
//
// Two catalogues would be free to drift, and a client would be told a tool
// exists on one transport and not the other. The two lists are compared as
// sorted sets, so order cannot hide a difference and a difference cannot hide
// behind order.
func TestHTTPToolSetIsIdenticalToTheStdioToolSet(t *testing.T) {
	ts := httpTestServer(t)
	httpNames := httpToolNames(t, ts.URL)
	stdioNames := ToolNames()

	if len(httpNames) != len(stdioNames) {
		t.Fatalf("HTTP has %d tools and stdio has %d", len(httpNames), len(stdioNames))
	}
	a := sortedNames(httpNames)
	b := sortedNames(stdioNames)
	for i := range a {
		if a[i] != b[i] {
			t.Fatalf("tool %d: HTTP has %q, stdio has %q\nHTTP:  %v\nstdio: %v", i, a[i], b[i], a, b)
		}
	}
}

// TestHTTPToolCallOnARealRun drives one real tool over HTTP against a real
// run directory.
func TestHTTPToolCallOnARealRun(t *testing.T) {
	dir := installTestRun(t)
	ts := httpTestServer(t)
	session := httpInitialize(t, ts.URL)

	body, err := json.Marshal(map[string]any{
		"jsonrpc": "2.0",
		"id":      3,
		"method":  "tools/call",
		"params":  map[string]any{"name": "dagrun_status", "arguments": map[string]any{"dir": dir}},
	})
	if err != nil {
		t.Fatal(err)
	}
	frame, _ := postRPC(t, ts.URL, session, string(body))
	result, _ := frame["result"].(map[string]any)
	if result == nil {
		t.Fatalf("tools/call returned no result: %v", frame)
	}
	if result["isError"] == true {
		t.Fatalf("tools/call reported an error: %v", result)
	}
	content, _ := result["content"].([]any)
	if len(content) == 0 {
		t.Fatalf("tools/call returned no content: %v", result)
	}
	block, _ := content[0].(map[string]any)
	text, _ := block["text"].(string)
	if !strings.Contains(text, "mcptest") {
		t.Errorf("the status payload does not name the run:\n%s", text)
	}
	if !strings.Contains(text, `"id": "1"`) {
		t.Errorf("the status payload does not list the nodes:\n%s", text)
	}
}

// TestARealMCPClientCanDriveTheHTTPTransport uses the official SDK's own
// client, so the transport is exercised the way a real client exercises it:
// connect, initialize, list, call.
func TestARealMCPClientCanDriveTheHTTPTransport(t *testing.T) {
	dir := installTestRun(t)
	ts := httpTestServer(t)

	client := sdkmcp.NewClient(&sdkmcp.Implementation{Name: "dagrun-test", Version: "test"}, nil)
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	session, err := client.Connect(ctx, &sdkmcp.StreamableClientTransport{Endpoint: ts.URL}, nil)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	defer session.Close()

	list, err := session.ListTools(ctx, nil)
	if err != nil {
		t.Fatalf("list tools: %v", err)
	}
	if len(list.Tools) != len(wantTools) {
		t.Fatalf("the client saw %d tools, want %d", len(list.Tools), len(wantTools))
	}

	res, err := session.CallTool(ctx, &sdkmcp.CallToolParams{
		Name:      "dagrun_status",
		Arguments: map[string]any{"dir": dir},
	})
	if err != nil {
		t.Fatalf("call tool: %v", err)
	}
	if res.IsError {
		t.Fatalf("the tool reported an error: %v", res.Content)
	}
	if len(res.Content) == 0 {
		t.Fatal("the tool returned no content")
	}
	text, _ := res.Content[0].(*sdkmcp.TextContent)
	if text == nil || !strings.Contains(text.Text, "mcptest") {
		t.Errorf("the tool payload does not name the run: %v", res.Content[0])
	}
}

// TestHTTPTransportRefusesANonLoopbackAddress is the exposure guard.
//
// This surface publishes a run directory with no authentication, so a
// non-loopback address is refused rather than served.
func TestHTTPTransportRefusesANonLoopbackAddress(t *testing.T) {
	for _, addr := range []string{"0.0.0.0:9999", "192.168.1.10:9999", ":9999", "example.com:80"} {
		tr, err := NewHTTPTransport(New(Config{Version: "test"}), addr)
		if err == nil {
			tr.ln.Close()
			t.Errorf("addr %q was accepted; it must be refused", addr)
			continue
		}
		if !strings.Contains(err.Error(), "loopback") && !strings.Contains(err.Error(), "no host") {
			t.Errorf("addr %q: the refusal does not say why: %v", addr, err)
		}
	}
}

// TestHTTPTransportAcceptsLoopback is the other half: the rule must not
// refuse the addresses it is meant to allow.
func TestHTTPTransportAcceptsLoopback(t *testing.T) {
	for _, addr := range []string{"127.0.0.1:0", "localhost:0", "[::1]:0"} {
		tr, err := NewHTTPTransport(New(Config{Version: "test"}), addr)
		if err != nil {
			t.Errorf("addr %q was refused: %v", addr, err)
			continue
		}
		tr.ln.Close()
	}
}

// TestHTTPTransportDefaultsToLoopbackEphemeral pins the default address.
func TestHTTPTransportDefaultsToLoopbackEphemeral(t *testing.T) {
	tr, err := NewHTTPTransport(New(Config{Version: "test"}), "")
	if err != nil {
		t.Fatal(err)
	}
	defer tr.ln.Close()
	if !strings.HasPrefix(tr.Addr(), "127.0.0.1:") {
		t.Errorf("the default address is %q, want a 127.0.0.1 one", tr.Addr())
	}
	if tr.ToolCount() != len(wantTools) {
		t.Errorf("the transport reports %d tools, want %d", tr.ToolCount(), len(wantTools))
	}
}
