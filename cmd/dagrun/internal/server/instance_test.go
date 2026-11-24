package server

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/KooshaPari/dagrun/internal/applet"
)

// The advertisement is the only thing that lets a host which did not start the
// server find it. It must appear once the port exists, carry the URLs that
// actually work, and be withdrawn on a clean stop.
func TestServerAdvertisesItselfOnBind(t *testing.T) {
	dir := fixture(t)
	registry := filepath.Join(t.TempDir(), "instances")
	s, err := New(Options{
		Dir:               dir,
		Addr:              "127.0.0.1:0",
		Version:           "1.2.3",
		EmbedAllowOrigins: []string{"http://console.example"},
		InstanceDir:       registry,
	})
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	if err := s.Bind(); err != nil {
		t.Fatalf("Bind: %v", err)
	}
	t.Cleanup(func() { _ = applet.RemoveInstance(registry, "") })

	instances, errs := applet.ReadInstances(registry)
	if len(errs) != 0 {
		t.Fatalf("registry has errors: %v", errs)
	}
	if len(instances) != 1 {
		t.Fatalf("got %d advertised instances, want 1", len(instances))
	}
	inst := instances[0]
	if inst.Origin != "http://"+s.Addr() {
		t.Fatalf("origin = %q, want the bound address %q", inst.Origin, s.Addr())
	}
	if inst.Version != "1.2.3" {
		t.Fatalf("version = %q, want the server's version", inst.Version)
	}
	if inst.Dir != dir {
		t.Fatalf("dir = %q, want %q", inst.Dir, dir)
	}
	if len(inst.AllowOrigins) != 1 || inst.AllowOrigins[0] != "http://console.example" {
		t.Fatalf("allow_origins = %v, want the server's frame policy", inst.AllowOrigins)
	}
	// The advertised manifest must be the one the server actually serves, not a
	// plausible-looking URL. This is the join a host depends on.
	status, body := get(t, s, applet.ContractPath)
	if status != 200 {
		t.Fatalf("manifest at the advertised path returned %d", status)
	}
	if !strings.Contains(body, `"id": "`+applet.ID+`"`) {
		t.Fatalf("manifest body does not identify applet %q:\n%s", applet.ID, body)
	}
}

func TestServerWithdrawsItsAdvertisementOnStop(t *testing.T) {
	dir := fixture(t)
	registry := filepath.Join(t.TempDir(), "instances")
	s, err := New(Options{Dir: dir, Addr: "127.0.0.1:0", Version: "9", InstanceDir: registry})
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- s.Listen(ctx) }()

	// Wait for the advertisement rather than sleeping a fixed time: the file is
	// written between Bind and Serve, so its presence is the readiness signal.
	deadline := time.Now().Add(5 * time.Second)
	for {
		instances, _ := applet.ReadInstances(registry)
		if len(instances) == 1 {
			break
		}
		if time.Now().After(deadline) {
			cancel()
			<-done
			t.Fatal("server never advertised itself")
		}
		time.Sleep(10 * time.Millisecond)
	}

	cancel()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("Listen: %v", err)
		}
	case <-time.After(10 * time.Second):
		t.Fatal("Listen did not return after cancel")
	}

	instances, errs := applet.ReadInstances(registry)
	if len(errs) != 0 || len(instances) != 0 {
		t.Fatalf("advertisement survived a clean stop: %d instances, %d errors", len(instances), len(errs))
	}
	entries, err := os.ReadDir(registry)
	if err != nil && !os.IsNotExist(err) {
		t.Fatalf("ReadDir: %v", err)
	}
	for _, e := range entries {
		t.Fatalf("registry still holds %q after a clean stop", e.Name())
	}
}

func TestServerWithoutInstanceDirDoesNotTouchTheFilesystem(t *testing.T) {
	dir := fixture(t)
	registry := filepath.Join(t.TempDir(), "instances")
	// Even with a registry configured in the environment, advertising is opt-in:
	// a library caller must not get a write it never asked for, so an empty
	// InstanceDir must leave no trace.
	t.Setenv(applet.InstanceDirEnv, registry)
	s, err := New(Options{Dir: dir})
	if err != nil {
		t.Fatalf("New: %v", err)
	}
	if err := s.Bind(); err != nil {
		t.Fatalf("Bind: %v", err)
	}
	defer func() { _ = s.ln.Close() }()
	instances, _ := applet.ReadInstances(registry)
	if len(instances) != 0 {
		t.Fatalf("a server with no InstanceDir advertised %d instances", len(instances))
	}
	if _, err := os.Stat(registry); !os.IsNotExist(err) {
		t.Fatalf("a server with no InstanceDir created %q", registry)
	}
}
