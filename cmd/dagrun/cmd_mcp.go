package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/KooshaPari/dagrun/internal/mcp"
)

const mcpHelp = `usage: dagrun mcp [--http ADDR]

Serve the Model Context Protocol.

With no flags the server speaks JSON-RPC over stdio: stdout carries the
protocol frames and nothing else, and every human-facing message goes to
stderr.

With --http it serves the same tools over the Streamable HTTP transport, so
one long-lived dagrun can serve many MCP clients.

  --http ADDR   listen address for the HTTP transport (default 127.0.0.1:0)
                an empty value means 127.0.0.1:0

The HTTP transport binds loopback only. A non-loopback address is refused:
this surface publishes a run directory with no authentication.

On HTTP it prints exactly one ready line to stdout, e.g.

  serving mcp http://127.0.0.1:52341  (tools 19)

and serves until SIGINT or SIGTERM, then exits 0.
`

// cmdMCP serves the Model Context Protocol over stdio or over HTTP.
//
// stdout is the protocol stream and nothing else on the stdio path:
// diagnostics go to stderr. On the HTTP path stdout carries the ready line,
// because there is no protocol stream on stdout to corrupt.
func cmdMCP(args []string) error {
	fs := flag.NewFlagSet("mcp", flag.ContinueOnError)
	fs.SetOutput(os.Stderr)
	fs.Usage = func() { fmt.Fprint(os.Stderr, mcpHelp) }
	httpAddr := &httpAddrFlag{}
	fs.Var(httpAddr, "http", "serve MCP over the Streamable HTTP transport on this loopback address")
	if err := fs.Parse(args); err != nil {
		return err
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	srv := mcp.New(mcp.Config{Version: Version, Log: os.Stderr})
	if httpAddr.set {
		return serveMCPHTTP(ctx, srv, httpAddr.addr)
	}
	return srv.Serve(ctx, os.Stdin, os.Stdout)
}

// httpAddrFlag is the --http flag.
//
// It is a flag.Value rather than a plain string because the flag package
// cannot tell "--http was not given" from "--http was given an empty value",
// and the two mean different things here: the first is stdio, the second is
// HTTP on the default loopback address.
type httpAddrFlag struct {
	addr string
	set  bool
}

func (f *httpAddrFlag) String() string { return f.addr }

func (f *httpAddrFlag) Set(v string) error {
	f.addr = v
	f.set = true
	return nil
}

// serveMCPHTTP serves the MCP tools over the Streamable HTTP transport.
//
// The ready line goes to stdout BEFORE serving starts, because the port is
// ephemeral unless the caller pinned one, so the URL only exists once the
// listener does.
func serveMCPHTTP(ctx context.Context, srv *mcp.Server, addr string) error {
	tr, err := mcp.NewHTTPTransport(srv, addr)
	if err != nil {
		return err
	}
	fmt.Printf("serving mcp http://%s  (tools %d)\n", tr.Addr(), tr.ToolCount())

	if err := tr.Serve(ctx); err != nil {
		// A cancelled context can surface as an error on some listener loops;
		// that still means "we were asked to stop", not "we failed".
		if !errors.Is(err, context.Canceled) {
			return err
		}
	}
	fmt.Fprintln(os.Stderr, "stopped")
	return nil
}
