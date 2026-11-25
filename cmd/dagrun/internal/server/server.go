// Package server exposes a running dagrun as a local read-only HTTP surface.
//
// Two jobs, one server, because they are the same data:
//
//   - the LIVE viz panel. `dagrun viz` writes one static file; a file cannot
//     show a run that is still moving. Here the HTML is rendered per request and
//     the page re-renders itself when the state changes.
//   - a small JSON API an agent or a monitoring tool can read, so "what is
//     running" does not require a shell round trip and a human eyeball.
//
// It is READ-ONLY by construction. There is no route that claims a node, takes
// a lease, or writes a file, and it does not open the store at all: it reads
// run.yaml and state.json directly. That is deliberate. A monitor must not sit on
// the write path, and the simplest way to guarantee that is to give it no way to
// write.
package server

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/KooshaPari/dagrun/internal/applet"
	"github.com/KooshaPari/dagrun/internal/plan"
	"github.com/KooshaPari/dagrun/internal/store"
)

// DefaultAddr is loopback with an ephemeral port. Anything else has to be asked
// for explicitly, because this surface has no authentication.
const DefaultAddr = "127.0.0.1:0"

// Options configures the server.
type Options struct {
	// Dir is the run directory holding run.yaml, state.json and trace/.
	Dir string
	// Addr is the listen address. Must be loopback.
	Addr string
	// Version is the binary's version, published in the applet manifest. An
	// empty value is reported as the contract-valid default rather than "".
	Version string
	// EmbedAllowOrigins names the consumer origins allowed to frame /embed, in
	// addition to this origin. Empty means same-origin only, which is the
	// default: this surface is unauthenticated, so widening it is a deliberate
	// act by whoever runs the server, never a convenience default.
	EmbedAllowOrigins []string
	// InstanceDir is where a bound server advertises itself, so a host that did
	// not start it (a tray icon, a launcher, a master console) can find it
	// without port scanning. Empty means do not advertise: a library must not
	// write to a home directory nobody asked it to touch, so this is opt-in and
	// only the `serve` command turns it on.
	InstanceDir string
}

// Server serves one run directory.
type Server struct {
	dir string
	// addr is set by Listen. Before that it holds the requested value.
	addr string
	// errOut receives panic reports. Defaults to os.Stderr.
	errOut io.Writer
	plan   *plan.Plan

	// mu guards the bound fields below. They are written by Listen and read by
	// callers that need the port before the serve loop starts, which is a
	// different goroutine, so an unsynchronised pair here would be a race.
	mu        sync.Mutex
	bound     bool
	boundAddr string
	// ln is the bound listener, created by Bind and consumed by Listen.
	ln net.Listener

	// appletManifest is built and validated once, in New. It is published to
	// strangers, so an invalid one is refused at construction rather than
	// served and trusted.
	appletManifest applet.Manifest
	// framePolicy is the effective CSP frame-ancestors value for /embed.
	framePolicy string
	// embedOrigins is the --embed-allow-origin list as given, published in the
	// instance record so a host can tell whether it is already allowed to frame
	// this server before it tries and reads a CSP violation.
	embedOrigins []string

	// instanceDir and instanceFile record where this server advertised itself,
	// so Listen can retract exactly the entry it wrote and never someone else's.
	instanceDir  string
	instanceFile string
}

// New validates the request without binding anything.
//
// It refuses a non-loopback address rather than trusting a caller to mean well:
// this server publishes a run directory with no auth, so "0.0.0.0" is not a
// preference, it is an incident.
func New(opt Options) (*Server, error) {
	dir := opt.Dir
	if strings.TrimSpace(dir) == "" {
		dir = ".dagrun"
	}
	abs, err := filepath.Abs(dir)
	if err != nil {
		return nil, err
	}

	addr := opt.Addr
	if strings.TrimSpace(addr) == "" {
		addr = DefaultAddr
	}
	if err := requireLoopback(addr); err != nil {
		return nil, err
	}

	raw, err := os.ReadFile(filepath.Join(abs, "run.yaml"))
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("no run at %s; install one with `dagrun plan FILE --dir %s`", abs, dir)
		}
		return nil, err
	}
	p, err := plan.Parse(raw)
	if err != nil {
		return nil, fmt.Errorf("parse %s/run.yaml: %w", abs, err)
	}

	// The manifest is validated here, not on each request: it cannot change
	// while the process lives, and a malformed one should stop the server
	// before it serves anything that claims to conform.
	manifest := applet.Build(opt.Version)
	if err := manifest.Validate(); err != nil {
		return nil, fmt.Errorf("applet manifest does not conform to %s: %w", applet.Contract, err)
	}
	frames, err := applet.FrameAncestors(opt.EmbedAllowOrigins)
	if err != nil {
		return nil, err
	}

	return &Server{
		dir: abs, addr: addr, errOut: os.Stderr, plan: p,
		appletManifest: manifest, framePolicy: frames, instanceDir: opt.InstanceDir,
		embedOrigins: opt.EmbedAllowOrigins,
	}, nil
}

// requireLoopback accepts localhost, 127.0.0.0/8 and ::1 only.
func requireLoopback(addr string) error {
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		return fmt.Errorf("addr %q is not host:port: %w", addr, err)
	}
	// An empty host (":8080") means every interface, so it is the one case that
	// looks loopback-ish and is the opposite. Refuse it.
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

// Addr is the bound address once Listen has bound it, otherwise "".
func (s *Server) Addr() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.bound {
		return s.boundAddr
	}
	return ""
}

// Handler returns the route table.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	// The applet contract document, where a discovery scanner looks first.
	mux.HandleFunc(applet.ContractPath, s.recover(s.handleAppletManifest))
	// dagrun's own discovery document: the manifest plus the deployment facts
	// the contract has no field for.
	mux.HandleFunc("/api/applet", s.recover(s.handleAppletDiscovery))
	// The embeddable read-only entrypoint a master console frames.
	mux.HandleFunc("/embed", s.recover(s.handleEmbed))
	mux.HandleFunc("/api/health", s.recover(s.handleHealth))
	mux.HandleFunc("/api/plan", s.recover(s.handlePlan))
	mux.HandleFunc("/api/status", s.recover(s.handleStatus))
	mux.HandleFunc("/api/agents", s.recover(s.handleAgents))
	mux.HandleFunc("/api/query", s.recover(s.handleQuery))
	mux.HandleFunc("/api/nodes/", s.recover(s.handleNode))
	// The viewer, but only for a page. An unmatched /api/ or /.well-known/ path
	// answers 404 JSON instead of this page (see handleFallback).
	mux.HandleFunc("/", s.recover(s.handleFallback))
	return mux
}

// Close releases the listener a Bind created.
//
// A caller can bind and then legitimately decide not to serve: a preflight that
// only wants to know whether the address and the manifest are usable, or a
// policy check that fails after the port exists. Before this, the only way to
// give the port back was to start serving and cancel the context, which meant a
// failed preflight leaked the port until the process exited.
func (s *Server) Close() error {
	if s.ln == nil {
		return nil
	}
	err := s.ln.Close()
	s.ln = nil
	return err
}

// Bind creates the listener and records the real address, without serving yet.
//
// It exists so a caller can print the URL BEFORE blocking in Listen. A ready
// line published after Listen returns is published when the server stops, which
// tells nobody anything; doing it in two steps is the only honest way to report
// an ephemeral port.
func (s *Server) Bind() error {
	if s.ln != nil {
		return nil
	}
	ln, err := net.Listen("tcp", s.addr)
	if err != nil {
		return err
	}
	s.ln = ln
	s.mu.Lock()
	s.bound = true
	s.boundAddr = ln.Addr().String()
	boundAddr := s.boundAddr
	s.mu.Unlock()

	// Advertise after the port exists, because the record carries the URL. A
	// failure here is a missing convenience, not a broken server: a host that
	// cannot read the registry can still be given the URL on stdout, so this
	// must not take the serve loop down.
	if s.instanceDir != "" {
		if inst, err := applet.NewInstance(s.appletManifest.Version, s.dir, boundAddr, s.embedOrigins); err != nil {
			fmt.Fprintf(s.errOut, "server: not advertising this instance: %v\n", err)
		} else if path, err := inst.Write(s.instanceDir); err != nil {
			fmt.Fprintf(s.errOut, "server: not advertising this instance: %v\n", err)
		} else {
			s.instanceFile = filepath.Base(path)
		}
	}
	return nil
}

// Listen binds (if Bind was not called) and serves until ctx is cancelled.
func (s *Server) Listen(ctx context.Context) error {
	if err := s.Bind(); err != nil {
		return err
	}
	// Withdraw the advertisement on the way out. A stale file is not fatal (a
	// consumer must confirm through the manifest anyway), but leaving one behind
	// on a clean stop would make every clean stop look like a crash.
	defer func() { _ = applet.RemoveInstance(s.instanceDir, s.instanceFile) }()
	ln := s.ln

	srv := &http.Server{Handler: s.Handler(), ReadHeaderTimeout: 10 * time.Second}
	errc := make(chan error, 1)
	go func() {
		err := srv.Serve(ln)
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

// recover turns a panic into a 500. A monitoring endpoint must never be able to
// take the process down, and a corrupt state file is exactly the kind of input
// that would otherwise do it.
func (s *Server) recover(h func(http.ResponseWriter, *http.Request)) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if v := recover(); v != nil {
				fmt.Fprintf(s.errOut, "server: panic serving %s: %v\n", r.URL.Path, v)
				http.Error(w, "internal error", http.StatusInternalServerError)
			}
		}()
		h(w, r)
	}
}

// loadState reads the state document without opening the store, because
// store.Open can create directories and a fresh state and this server must not
// write anything.
func (s *Server) loadState() (*store.State, error) {
	raw, err := os.ReadFile(filepath.Join(s.dir, "state.json"))
	if err != nil {
		if os.IsNotExist(err) {
			// A planned-but-unrun directory is a legitimate state: every node is
			// pending, which is the truth.
			st := &store.State{Run: s.plan.Run, Nodes: map[string]*store.NodeState{}}
			for _, n := range s.plan.Nodes {
				if n != nil {
					st.Nodes[n.ID] = &store.NodeState{Status: plan.StatusPending}
				}
			}
			return st, nil
		}
		return nil, err
	}
	var st store.State
	if err := json.Unmarshal(raw, &st); err != nil {
		return nil, fmt.Errorf("corrupt state in %s: %w", s.dir, err)
	}
	if st.Nodes == nil {
		st.Nodes = map[string]*store.NodeState{}
	}
	return &st, nil
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	_ = enc.Encode(v)
}
