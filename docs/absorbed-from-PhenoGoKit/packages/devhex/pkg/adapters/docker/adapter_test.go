package docker_test

import (
	"context"
	"testing"

	"github.com/KooshaPari/devenv-abstraction/pkg/adapters/docker"
	"github.com/KooshaPari/devenv-abstraction/pkg/domain"
)

// TestCompileTimeContract verifies that docker.Adapter implements domain.Environment.
func TestCompileTimeContract(t *testing.T) {
	// This is a compile-time check; if it compiles, the contract is satisfied.
	var _ domain.Environment = (*docker.Adapter)(nil)
}

// TestNew verifies that New() returns a valid adapter without error.
func TestNew(t *testing.T) {
	adapter, err := docker.New()
	if err != nil {
		// Docker may not be available in CI; this is expected to fail gracefully.
		t.Skipf("Docker not available (expected in CI without Docker): %v", err)
	}
	if adapter == nil {
		t.Fatal("expected non-nil adapter")
	}
}

// TestStatus_NoContainerReturnsStopped verifies the no-op Status path.
// This does not require a live Docker daemon.
func TestStatus_NoContainerReturnsStopped(t *testing.T) {
	adapter, err := docker.New()
	if err != nil {
		t.Skipf("Docker not available: %v", err)
	}
	status, err := adapter.Status(context.Background())
	if err != nil {
		t.Fatalf("Status on idle adapter returned error: %v", err)
	}
	if status.Code != domain.StatusStopped {
		t.Errorf("expected StatusStopped for idle adapter, got %q", status.Code)
	}
}

// TestStop_NoContainerReturnsError verifies Stop reports an error when no container is running.
func TestStop_NoContainerReturnsError(t *testing.T) {
	adapter, err := docker.New()
	if err != nil {
		t.Skipf("Docker not available: %v", err)
	}
	if err := adapter.Stop(context.Background()); err == nil {
		t.Fatal("expected error when stopping adapter with no active container, got nil")
	}
}

// TestStart_ReturnsNotImplemented guards the TODO boundary until WP02 lands.
func TestStart_ReturnsNotImplemented(t *testing.T) {
	adapter, err := docker.New()
	if err != nil {
		t.Skipf("Docker not available: %v", err)
	}
	err = adapter.Start(context.Background(), domain.Config{Name: "test"})
	if err == nil {
		t.Fatal("expected not-implemented error from Start")
	}
}

// TestExec_ReturnsNotImplemented guards the TODO boundary until WP03 lands.
func TestExec_ReturnsNotImplemented(t *testing.T) {
	adapter, err := docker.New()
	if err != nil {
		t.Skipf("Docker not available: %v", err)
	}
	_, err = adapter.Exec(context.Background(), []string{"echo", "hi"})
	if err == nil {
		t.Fatal("expected not-implemented error from Exec")
	}
}

// TestLogs_ReturnsNotImplemented guards the TODO boundary until WP03 lands.
func TestLogs_ReturnsNotImplemented(t *testing.T) {
	adapter, err := docker.New()
	if err != nil {
		t.Skipf("Docker not available: %v", err)
	}
	rc, err := adapter.Logs(context.Background())
	if err == nil {
		if rc != nil {
			rc.Close()
		}
		t.Fatal("expected not-implemented error from Logs")
	}
}
