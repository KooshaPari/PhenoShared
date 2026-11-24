package applet

// The instance registry: how a host that did not start this server finds one.
//
// Every other route is push-shaped: a console can embed /embed, but only if it
// already knows the URL. A tray app, a menu bar item, or a launcher cannot port
// scan, and `dagrun serve` prints its port to a terminal nobody is watching. So a
// running server advertises itself in a small file, and a host reads the
// directory.
//
// The registry is a HINT, never an authority. A killed process leaves its file
// behind, and a pid can be recycled, so a consumer must confirm an entry by
// fetching its manifest. Nothing here treats a file's existence as proof that
// the server behind it is alive.

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// InstanceDirEnv overrides where instances are advertised. It exists so a test
// and a container can point at a scratch directory instead of the home one.
const InstanceDirEnv = "DAGRUN_INSTANCE_DIR"

// Instance is one running server, as a file a host can read.
//
// It carries the three URLs rather than one base URL because a host should not
// have to concatenate paths to guess where a contract document lives; the file's
// whole job is to remove that guesswork.
type Instance struct {
	// Contract is the applet contract id, so a host can reject a file written
	// by a different surface that happens to share this directory.
	Contract string `json:"contract"`
	// ID is stable for one bound address: host_port, not the pid, because the
	// same run directory can be served twice and the port is what differs.
	ID string `json:"id"`
	// Origin is the scheme://host:port a frame policy is expressed against.
	Origin string `json:"origin"`
	// Manifest, Discovery and Embed are absolute URLs on Origin.
	Manifest  string `json:"manifest"`
	Discovery string `json:"discovery"`
	Embed     string `json:"embed"`
	// Dir is the absolute run directory being served.
	Dir string `json:"dir"`
	// Version is the binary's version, as published in the manifest.
	Version string `json:"version"`
	// PID is the process that wrote the file. It is a pointer, not an identity:
	// a consumer that cares must confirm through Manifest, never through the pid.
	PID int `json:"pid"`
	// StartedAt is RFC 3339 UTC. A host can use it to prefer the newest
	// instance when several are advertised, which is what a human means by
	// "the one I just started".
	StartedAt string `json:"started_at"`
	// ReadOnly restates the server's own guarantee. It is a field rather than
	// an assumption so a host never has to remember which surfaces may write.
	ReadOnly bool `json:"read_only"`
	// AllowOrigins is the effective --embed-allow-origin list, so a host can
	// tell whether it is already allowed to frame Embed before trying.
	AllowOrigins []string `json:"allow_origins"`
}

// DefaultInstanceDir is where running servers advertise themselves:
// $DAGRUN_INSTANCE_DIR, else <config>/instances, else ~/.dagrun/instances.
func DefaultInstanceDir() (string, error) {
	if dir := strings.TrimSpace(os.Getenv(InstanceDirEnv)); dir != "" {
		return dir, nil
	}
	if config, err := os.UserConfigDir(); err == nil {
		return filepath.Join(config, "dagrun", "instances"), nil
	}
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("cannot locate a directory for instance files: %w", err)
	}
	return filepath.Join(home, ".dagrun", "instances"), nil
}

// NewInstance builds the record for a bound address.
//
// It refuses a non-loopback origin. The registry is read by unpickled host code
// on the same machine, and this server has no authentication: advertising an
// address a stranger can reach would turn a local hint into a published
// unauthenticated surface.
func NewInstance(version, runDir, boundAddr string, allowOrigins []string) (Instance, error) {
	host, port, err := net.SplitHostPort(boundAddr)
	if err != nil {
		return Instance{}, fmt.Errorf("bound address %q is not host:port: %w", boundAddr, err)
	}
	ip := net.ParseIP(host)
	if ip == nil || !ip.IsLoopback() {
		return Instance{}, fmt.Errorf("bound address %q is not loopback; the applet surface is unauthenticated and must not be advertised", boundAddr)
	}
	origin := "http://" + net.JoinHostPort(host, port)
	allow := append([]string{}, allowOrigins...)
	sort.Strings(allow)
	return Instance{
		Contract:     Contract,
		ID:           safeID(host) + "_" + port,
		Origin:       origin,
		Manifest:     origin + ContractPath,
		Discovery:    origin + "/api/applet",
		Embed:        origin + "/embed",
		Dir:          runDir,
		Version:      version,
		PID:          os.Getpid(),
		StartedAt:    time.Now().UTC().Format(time.RFC3339),
		ReadOnly:     true,
		AllowOrigins: allow,
	}, nil
}

// safeID turns a bound host into a file-name-safe token. An IPv6 loopback
// address is written `::1`, and `:` is legal in a POSIX file name but illegal on
// Windows, which is a supported host here, so the separator is normalised rather
// than merely tolerated.
func safeID(host string) string {
	return strings.NewReplacer(":", "-", "[", "", "]", "").Replace(host)
}

// Validate checks a record read from disk.
//
// A file is untrusted input even when we wrote it: it may be stale, hand-edited,
// or written by a future version. The checks are the ones a host relies on, so a
// host that validates once does not have to re-derive them.
func (i Instance) Validate() error {
	if i.Contract != Contract {
		return fmt.Errorf("contract %q is not %q", i.Contract, Contract)
	}
	if i.ID == "" {
		return fmt.Errorf("id is empty")
	}
	u, err := url.Parse(i.Origin)
	if err != nil {
		return fmt.Errorf("origin %q is not a URL: %w", i.Origin, err)
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return fmt.Errorf("origin %q must be http or https", i.Origin)
	}
	host := u.Hostname()
	ip := net.ParseIP(host)
	localName := host == "localhost"
	if (ip == nil || !ip.IsLoopback()) && !localName {
		return fmt.Errorf("origin %q is not loopback", i.Origin)
	}
	if u.Path != "" && u.Path != "/" {
		return fmt.Errorf("origin %q has a path; an origin is scheme://host:port", i.Origin)
	}
	for _, f := range []struct{ name, v string }{
		{"manifest", i.Manifest}, {"discovery", i.Discovery}, {"embed", i.Embed},
	} {
		if !strings.HasPrefix(f.v, i.Origin+"/") {
			return fmt.Errorf("%s %q is not on origin %s", f.name, f.v, i.Origin)
		}
	}
	if i.StartedAt == "" {
		return fmt.Errorf("started_at is empty")
	}
	if _, err := time.Parse(time.RFC3339, i.StartedAt); err != nil {
		return fmt.Errorf("started_at %q is not RFC 3339: %w", i.StartedAt, err)
	}
	if !i.ReadOnly {
		return fmt.Errorf("read_only is false; this surface has no write path, so a file claiming otherwise was not written by it")
	}
	if i.AllowOrigins == nil {
		return fmt.Errorf("allow_origins is nil; an empty list is the default and must be stated")
	}
	return nil
}

// FileName is the instance's file name, derived from ID rather than the pid so a
// restart on the same port replaces its own entry instead of accumulating.
func (i Instance) FileName() (string, error) {
	if i.ID == "" {
		return "", fmt.Errorf("instance has no id")
	}
	if strings.ContainsAny(i.ID, `/\`) || strings.Contains(i.ID, "..") {
		return "", fmt.Errorf("instance id %q is not a safe file name", i.ID)
	}
	return i.ID + ".json", nil
}

// Write atomically publishes the instance in dir, creating dir if needed.
//
// Atomic because a reader can run at any moment: a half-written file would be a
// corrupt entry, and a corrupt entry is exactly what makes a launcher show a
// console that cannot be reached. Write-then-rename in the same directory is the
// only form that is safe for a concurrent reader on every platform.
func (i Instance) Write(dir string) (string, error) {
	if err := i.Validate(); err != nil {
		return "", err
	}
	name, err := i.FileName()
	if err != nil {
		return "", err
	}
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return "", err
	}
	body, err := json.MarshalIndent(i, "", "  ")
	if err != nil {
		return "", err
	}
	body = append(body, '\n')

	var suffix [8]byte
	if _, err := rand.Read(suffix[:]); err != nil {
		return "", fmt.Errorf("cannot name a temp file: %w", err)
	}
	tmp := filepath.Join(dir, "."+name+"."+hex.EncodeToString(suffix[:])+".tmp")
	// 0600: the record names a local port serving a run directory. That is
	// unremarkable on a single-user machine and nothing a second account needs.
	if err := os.WriteFile(tmp, body, 0o600); err != nil {
		return "", err
	}
	path := filepath.Join(dir, name)
	if err := os.Rename(tmp, path); err != nil {
		_ = os.Remove(tmp)
		return "", err
	}
	return path, nil
}

// RemoveInstance deletes one entry. It is idempotent: a server that never
// advertised itself, or one that already removed its file, is not an error.
func RemoveInstance(dir, name string) error {
	if name == "" {
		return nil
	}
	err := os.Remove(filepath.Join(dir, name))
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}

// ReadInstances returns every valid entry in dir, newest first, plus one error
// per file that could not be read.
//
// A bad file does not suppress the good ones. A launcher that refused to show any
// console because one stale file was corrupt would be worse than useless, so the
// errors are returned for reporting and the valid entries are still returned.
func ReadInstances(dir string) ([]Instance, []error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, []error{err}
	}
	var out []Instance
	var errs []error
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".json") || strings.HasPrefix(e.Name(), ".") {
			continue
		}
		path := filepath.Join(dir, e.Name())
		body, err := os.ReadFile(path)
		if err != nil {
			errs = append(errs, err)
			continue
		}
		dec := json.NewDecoder(strings.NewReader(string(body)))
		dec.DisallowUnknownFields()
		var inst Instance
		if err := dec.Decode(&inst); err != nil {
			errs = append(errs, fmt.Errorf("%s: %w", e.Name(), err))
			continue
		}
		if err := inst.Validate(); err != nil {
			errs = append(errs, fmt.Errorf("%s: %w", e.Name(), err))
			continue
		}
		out = append(out, inst)
	}
	sort.Slice(out, func(a, b int) bool { return out[a].StartedAt > out[b].StartedAt })
	return out, errs
}
