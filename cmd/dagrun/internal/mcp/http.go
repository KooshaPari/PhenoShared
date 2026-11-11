package mcp

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net"
	"net/http"
	"strings"
	"time"

	sdkmcp "github.com/modelcontextprotocol/go-sdk/mcp"
)

// DefaultHTTPAddr is loopback with an ephemeral port.
//
// Anything else has to be asked for explicitly, because this surface has no
// authentication.
const DefaultHTTPAddr = "127.0.0.1:0"

// HTTPTransport serves the dagrun MCP tools over the Streamable HTTP
// transport, so one long-lived dagrun can serve many MCP clients instead of
// one process per client.
//
// The tools are not re-declared here. The catalogue in registry.go is
// registered with the official Go SDK, so the HTTP transport and the stdio
// transport cannot advertise different tools: there is only one list.
type HTTPTransport struct {
	server *Server
	// addr is the bound address. It is only known once the listener exists,
	// because the default port is ephemeral.
	addr string
	ln   net.Listener
}

// NewHTTPTransport validates addr and binds the listener.
//
// It refuses a non-loopback address rather than trusting a caller to mean
// well: this transport publishes a run directory with no auth, so "0.0.0.0" is
// not a preference, it is an incident.
//
// The listener is bound here, before Serve, so a caller can print the URL
// before the blocking call. A ready line published after Serve returns is
// published when the server stops, which tells nobody anything.
func NewHTTPTransport(s *Server, addr string) (*HTTPTransport, error) {
	if strings.TrimSpace(addr) == "" {
		addr = DefaultHTTPAddr
	}
	if err := requireLoopback(addr); err != nil {
		return nil, err
	}
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, err
	}
	return &HTTPTransport{server: s, addr: ln.Addr().String(), ln: ln}, nil
}

// Addr is the bound address, host:port.
func (t *HTTPTransport) Addr() string { return t.addr }

// ToolCount is how many tools the shared catalogue holds.
func (t *HTTPTransport) ToolCount() int { return len(toolSpecs()) }

// Serve serves until ctx is cancelled, then shuts down gracefully.
//
// A cancelled context is a normal stop, not a failure: Ctrl-C on a server
// means "stop", and the process exits 0.
func (t *HTTPTransport) Serve(ctx context.Context) error {
	srv := &http.Server{Handler: t.server.HTTPHandler(), ReadHeaderTimeout: 10 * time.Second}
	errc := make(chan error, 1)
	go func() {
		err := srv.Serve(t.ln)
		if errors.Is(err, http.ErrServerClosed) {
			err = nil
		}
		errc <- err
	}()

	select {
	case <-ctx.Done():
		shutCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(shutCtx)
		return nil
	case err := <-errc:
		return err
	}
}

// HTTPHandler returns the official Go SDK's Streamable HTTP handler for the
// shared catalogue.
//
// Every tool is registered with the same name, description and input schema
// the stdio transport advertises, and every call goes through the same
// dispatch, so the two transports answer identically.
func (s *Server) HTTPHandler() http.Handler {
	srv := sdkmcp.NewServer(&sdkmcp.Implementation{Name: "dagrun", Version: s.version}, nil)
	for _, spec := range toolSpecs() {
		srv.AddTool(&sdkmcp.Tool{
			Name:        spec.Name,
			Description: spec.Description,
			InputSchema: spec.InputSchema,
		}, func(ctx context.Context, req *sdkmcp.CallToolRequest) (*sdkmcp.CallToolResult, error) {
			var raw json.RawMessage
			if req.Params != nil {
				raw = req.Params.Arguments
			}
			payload, isError, err := s.callTool(ctx, spec.Name, raw)
			if err != nil {
				// A protocol-level error (an unknown tool, arguments that are
				// not JSON) belongs in the JSON-RPC error, not in the result:
				// the SDK treats a returned error as a protocol error, which
				// is exactly what the stdio transport does with it too.
				return nil, err
			}
			return &sdkmcp.CallToolResult{
				Content: []sdkmcp.Content{&sdkmcp.TextContent{Text: encodeText(payload)}},
				IsError: isError,
			}, nil
		})
	}
	return sdkmcp.NewStreamableHTTPHandler(func(*http.Request) *sdkmcp.Server { return srv }, &sdkmcp.StreamableHTTPOptions{})
}

// requireLoopback accepts localhost, 127.0.0.0/8 and ::1 only.
//
// This mirrors internal/server's requireLoopback, which is unexported and
// therefore cannot be reused from here. The rule is duplicated on purpose
// rather than exported across packages: the two surfaces publish different
// things (a run directory and the MCP tools over it), but they have the same
// exposure, so they have the same rule.
//
// An empty host (":8080") means every interface, so it is the one case that
// looks loopback-ish and is the opposite. Refuse it.
func requireLoopback(addr string) error {
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		return fmt.Errorf("addr %q is not host:port: %w", addr, err)
	}
	if host == "" {
		return fmt.Errorf("addr %q has no host, which binds every interface: name 127.0.0.1 explicitly", addr)
	}
	if strings.EqualFold(host, "localhost") {
		return nil
	}
	if ip := net.ParseIP(host); ip != nil && ip.IsLoopback() {
		return nil
	}
	return fmt.Errorf("addr %q is not loopback: this server serves a run directory with no authentication, so it binds 127.0.0.1 (or ::1) only", addr)
}
